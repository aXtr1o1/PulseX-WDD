"""
Test Admin Authentication wall with ADMIN_AUTH_MODE controls.
"""
def test_admin_auth_cookie_mode(client, set_admin_bypass):
    set_admin_bypass("cookie")
    
    # Needs auth
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 401
    
    # Wrong password
    res_wrong = client.post("/api/admin/login", json={"password": "wrongpassword123"})
    assert res_wrong.status_code == 401
    
    # Correct password
    from apps.api.app.config import get_settings
    pwd = get_settings().admin_password
    res_login = client.post("/api/admin/login", json={"password": pwd})
    assert res_login.status_code == 200
    assert "pulsex_admin" in res_login.cookies
    
    # Access dashboard with cookie
    cookies = res_login.cookies
    res_dash = client.get("/api/admin/dashboard", cookies=cookies)
    assert res_dash.status_code == 200
    
    # Logout clears cookie
    res_logout = client.post("/api/admin/logout", cookies=cookies)
    assert res_logout.status_code == 200
    assert not res_logout.cookies.get("pulsex_admin")
    
    # Access removed
    res_dash_again = client.get("/api/admin/dashboard")
    assert res_dash_again.status_code == 401

def test_admin_auth_off_mode(client, set_admin_bypass):
    set_admin_bypass("off")
    
    # Immediate access without cookie
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 200
