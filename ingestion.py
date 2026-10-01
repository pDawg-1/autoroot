"""Validated, idempotent append of complete weekly CSV batches."""
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import hashlib
import io
import json
import os
from datetime import datetime, timezone
import pandas as pd
from warehouse import validate

KEYS = ["week", "region", "sku", "channel"]
COLUMNS = KEYS+["units", "revenue"]
MAX_BYTES = 30*1024*1024

def read_feed(source):
    if hasattr(source,"read"):
        raw=source.read(MAX_BYTES+1)
    elif str(source).startswith("https://"):
        req=Request(str(source),headers={"User-Agent":"AutoRoot/2.0"})
        with urlopen(req,timeout=30) as response:
            if not response.geturl().startswith("https://"):
                raise ValueError("Feed redirects must remain HTTPS")
            raw=response.read(MAX_BYTES+1)
    elif "://" in str(source):
        raise ValueError("Remote feeds require HTTPS")
    else:
        with open(source,"rb") as file:
            raw=file.read(MAX_BYTES+1)
    if isinstance(raw,str):
        raw=raw.encode("utf-8")
    if len(raw)>MAX_BYTES:
        raise ValueError("Feed exceeds the 30 MB limit")
    return raw

def parse_sales(raw):
    frame=pd.read_csv(io.BytesIO(raw),dtype={"region":"string","sku":"string","channel":"string"})
    if not set(COLUMNS).issubset(frame.columns):
        raise ValueError("Missing required sales columns")
    frame=frame[COLUMNS].copy()
    frame["week"]=pd.to_datetime(frame.week,format="%Y-%m-%d",errors="raise")
    for dim in KEYS[1:]:
        frame[dim]=frame[dim].str.strip()
        if frame[dim].eq("").any():
            raise ValueError("Empty segment labels")
    for column in ["units","revenue"]:
        frame[column]=pd.to_numeric(frame[column],errors="raise")
    validate(frame)
    frame["units"]=frame.units.astype("int64")
    return frame.sort_values(KEYS).reset_index(drop=True)

def merge_sales(existing, incoming):
    validate(existing)
    validate(incoming)
    old=existing.set_index(KEYS)
    new=incoming.set_index(KEYS)
    overlap=old.index.intersection(new.index)
    if len(overlap):
        if not old.loc[overlap,["units","revenue"]].eq(new.loc[overlap,["units","revenue"]]).all().all():
            raise ValueError("Conflicting values for an existing segment-week; corrections require explicit review")
    additions=incoming[~pd.MultiIndex.from_frame(incoming[KEYS]).isin(old.index)]
    if not additions.empty and additions.week.min()<=existing.week.max():
        raise ValueError("Only later complete weeks may be appended")
    combined=pd.concat([existing,additions],ignore_index=True).sort_values(KEYS).reset_index(drop=True)
    validate(combined)
    return combined,dict(added_rows=len(additions),added_weeks=int(additions.week.nunique()),duplicate_rows=len(overlap))

def write_atomic(frame,path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    frame.to_csv(temporary,index=False,date_format="%Y-%m-%d")
    os.replace(temporary,path)

def ingest(source,directory,source_kind="external",operations_source=None):
    directory=Path(directory)
    incoming=parse_sales(read_feed(source))
    path=directory/"sales.csv"
    existing=parse_sales(path.read_bytes()) if path.exists() else None
    if existing is None:
        combined=incoming
        result=dict(added_rows=len(incoming),added_weeks=int(incoming.week.nunique()),duplicate_rows=0)
    else:
        combined,result=merge_sales(existing,incoming)
    operations=None
    if operations_source is not None:
        from decision import validate_operations
        operations=pd.read_csv(io.BytesIO(read_feed(operations_source)),parse_dates=["week"])
        existing_ops=directory/"operations.csv"
        if existing_ops.exists():
            previous=pd.read_csv(existing_ops,parse_dates=["week"])
            overlap=previous.set_index(KEYS).index.intersection(operations.set_index(KEYS).index)
            if len(overlap) and not previous.set_index(KEYS).loc[overlap].eq(operations.set_index(KEYS).loc[overlap]).all().all():
                raise ValueError("Conflicting operational records require explicit review")
            operations=pd.concat([previous,operations]).drop_duplicates(KEYS).sort_values(KEYS).reset_index(drop=True)
        validate_operations(operations,combined)
    if operations is not None:
        write_atomic(operations,directory/"operations.csv")
    write_atomic(combined,path)
    state={**result,"source_kind":source_kind,"processed_at":datetime.now(timezone.utc).isoformat(),"last_week":combined.week.max().strftime("%Y-%m-%d"),"rows":len(combined),"weeks":int(combined.week.nunique()),"sales_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    (directory/"state.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
    return combined,state
