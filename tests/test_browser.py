from tracker.browser_fetcher import build_launch_kwargs, detect_proxy


def test_detect_proxy_prefers_https():
    env = {"HTTP_PROXY": "http://plain:1", "HTTPS_PROXY": "http://secure:2"}
    assert detect_proxy(env) == "http://secure:2"


def test_detect_proxy_falls_back_to_http_and_lowercase():
    assert detect_proxy({"http_proxy": "http://p:3"}) == "http://p:3"
    assert detect_proxy({"https_proxy": "http://q:4"}) == "http://q:4"


def test_detect_proxy_none_when_unset():
    assert detect_proxy({}) is None


def test_launch_kwargs_wires_proxy_when_present():
    kwargs = build_launch_kwargs("http://127.0.0.1:33465")
    assert kwargs["proxy"] == {"server": "http://127.0.0.1:33465"}
    assert kwargs["headless"] is True
    assert "--no-sandbox" in kwargs["args"]


def test_launch_kwargs_omits_proxy_when_absent():
    kwargs = build_launch_kwargs(None)
    assert "proxy" not in kwargs
    assert "--no-sandbox" in kwargs["args"]
