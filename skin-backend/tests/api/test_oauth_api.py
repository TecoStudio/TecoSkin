import pytest
from urllib.parse import urlparse, parse_qs
from io import BytesIO

from PIL import Image


@pytest.mark.asyncio
async def test_admin_manage_oauth_apps(client, admin_headers):
    headers = {"Authorization": admin_headers["Authorization"]}

    create_resp = await client.post(
        "/admin/oauth/apps",
        json={
            "client_name": "Forum Login",
            "redirect_uri": "https://forum.example.com/oauth/callback",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["app_id"] >= 1
    assert created["client_secret"]

    list_resp = await client.get("/admin/oauth/apps", headers=headers)
    assert list_resp.status_code == 200
    apps = list_resp.json()
    assert any(app["app_id"] == created["app_id"] for app in apps)

    update_resp = await client.put(
        f"/admin/oauth/apps/{created['app_id']}",
        json={
            "client_name": "Forum Login V2",
            "redirect_uri": "https://forum.example.com/oauth/callback2",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200


@pytest.mark.asyncio
async def test_oauth_authorize_and_token_exchange(client, admin_headers, auth_headers):
    admin_h = {"Authorization": admin_headers["Authorization"]}
    user_h = {"Authorization": auth_headers["Authorization"]}

    create_profile_resp = await client.post(
        "/me/profiles",
        json={"name": "OAuthSkinPlayer", "model": "default"},
        headers=user_h,
    )
    assert create_profile_resp.status_code == 200
    profile_id = create_profile_resp.json()["id"]

    skin_file = BytesIO()
    Image.new("RGBA", size=(64, 64), color=(40, 160, 220, 255)).save(skin_file, "png")
    skin_file.seek(0)
    upload_resp = await client.post(
        "/me/textures",
        data={"texture_type": "skin", "note": "OAuth Skin", "is_public": "false", "model": "default"},
        files={"file": ("oauth-skin.png", skin_file, "image/png")},
        headers=user_h,
    )
    assert upload_resp.status_code == 200
    skin_hash = upload_resp.json()["hash"]

    apply_resp = await client.post(
        f"/me/textures/{skin_hash}/apply",
        json={"profile_id": profile_id, "texture_type": "skin"},
        headers=user_h,
    )
    assert apply_resp.status_code == 200

    create_resp = await client.post(
        "/admin/oauth/apps",
        json={
            "client_name": "Ext App",
            "redirect_uri": "https://ext.example.com/callback",
        },
        headers=admin_h,
    )
    assert create_resp.status_code == 200
    app = create_resp.json()

    check_resp = await client.get(
        "/oauth/authorize/check",
        params={
            "client_id": app["app_id"],
            "redirect_uri": app["redirect_uri"],
            "state": "s123",
            "scope": "userinfo email skin",
        },
    )
    assert check_resp.status_code == 200
    check_data = check_resp.json()
    assert check_data["site_name"]
    assert check_data["requester_name"]
    assert check_data["scope"] == "userinfo email skin"
    assert any(item["key"] == "skin" for item in check_data["scope_items"])

    decision_resp = await client.post(
        "/oauth/authorize/decision",
        json={
            "client_id": app["app_id"],
            "redirect_uri": app["redirect_uri"],
            "state": "s123",
            "scope": "userinfo email skin",
            "approved": True,
        },
        headers=user_h,
    )
    assert decision_resp.status_code == 200
    redirect_url = decision_resp.json()["redirect_url"]

    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    assert params.get("state") == ["s123"]
    assert "code" in params
    code = params["code"][0]

    token_resp = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": str(app["app_id"]),
            "client_secret": app["client_secret"],
            "redirect_uri": app["redirect_uri"],
        },
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert token_data["token_type"] == "Bearer"
    assert token_data.get("access_token")

    userinfo_resp = await client.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert userinfo_resp.status_code == 200
    userinfo = userinfo_resp.json()
    assert userinfo["sub"] == auth_headers["X-User-ID"]
    assert userinfo.get("username")
    assert userinfo.get("avatar_url")
    assert userinfo.get("email")

    profile_resp = await client.get(
        "/oauth/profile",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert profile_resp.status_code == 200
    assert profile_resp.json().get("username")

    avatar_resp = await client.get(
        "/oauth/avatar",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert avatar_resp.status_code == 200
    assert avatar_resp.json().get("avatar_url")

    email_resp = await client.get(
        "/oauth/email",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert email_resp.status_code == 200
    assert email_resp.json().get("email")

    skin_resp = await client.get(
        "/oauth/skin",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert skin_resp.status_code == 200
    assert skin_resp.headers.get("content-type", "").startswith("image/png")
    assert skin_resp.headers.get("x-vskin-profile-id") == profile_id
    assert skin_resp.headers.get("x-vskin-skin-hash") == skin_hash
    assert skin_resp.content


@pytest.mark.asyncio
async def test_oauth_permissions_endpoint(client, admin_headers, auth_headers):
    admin_h = {"Authorization": admin_headers["Authorization"]}
    user_h = {"Authorization": auth_headers["Authorization"]}

    create_resp = await client.post(
        "/admin/oauth/apps",
        json={
            "client_name": "Perm App",
            "redirect_uri": "https://ext.example.com/perm-callback",
        },
        headers=admin_h,
    )
    app = create_resp.json()

    decision_resp = await client.post(
        "/oauth/authorize/decision",
        json={
            "client_id": app["app_id"],
            "redirect_uri": app["redirect_uri"],
            "state": "sperm",
            "scope": "permission",
            "approved": True,
        },
        headers=user_h,
    )
    redirect_url = decision_resp.json()["redirect_url"]
    code = parse_qs(urlparse(redirect_url).query)["code"][0]

    token_resp = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": str(app["app_id"]),
            "client_secret": app["client_secret"],
            "redirect_uri": app["redirect_uri"],
        },
    )
    token_data = token_resp.json()

    perm_resp = await client.get(
        "/oauth/permissions",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert perm_resp.status_code == 200
    payload = perm_resp.json()
    assert payload.get("user_group") in {"user", "teacher", "admin", "super_admin"}
    assert payload.get("user_group_meta", {}).get("title")
