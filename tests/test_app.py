from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_app_initial_load_and_metric_switch():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=120).run()
    assert not app.exception
    assert len(app.metric)>=4
    app.sidebar.selectbox[0].select("units").run()
    assert not app.exception
    app.sidebar.toggle[0].set_value(False).run()
    assert not app.exception
    app.sidebar.selectbox[1].select("rolling_z").run()
    assert not app.exception
