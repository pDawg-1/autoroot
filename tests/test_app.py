from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_app_initial_load_and_metric_switch():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=120).run()
    assert not app.exception
    assert len(app.metric)>=4
    app.selectbox(key="metric").select("units").run()
    assert not app.exception
    app.toggle(key="alerts_only").set_value(False).run()
    assert not app.exception
    app.selectbox(key="method").select("rolling_z").run()
    assert not app.exception
    app.selectbox(key="source").select("Upload sales CSV").run()
    assert not app.exception
    assert "Upload" in app.info[0].value

def test_uploaded_feed_is_computed_without_demo_labels():
    import io
    from unittest.mock import patch
    from generate_data import generate
    sales=generate()[0]
    small=sales[(sales.region=="West")&(sales.sku=="Cola 750ml")&(sales.channel=="Online")].head(30)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=120)
    app.session_state["source"]="Upload sales CSV"
    def uploader(label,*args,**kwargs):
        return io.BytesIO(small.to_csv(index=False).encode()) if label=="Sales CSV" else None
    with patch("streamlit.file_uploader",side_effect=uploader):
        app.run()
        assert not app.exception
        assert app.metric[0].value
        assert any("No labeled outcomes" in element.value for element in app.info)
        assert any("Unverified sales movement" in element.value for element in app.markdown)
        app.selectbox(key="metric").select("units").run()
        assert not app.exception
