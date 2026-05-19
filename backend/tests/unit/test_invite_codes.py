from app.utils.invite_codes import generate_invite_code


def test_generate_invite_code_format():
    code = generate_invite_code()
    assert code.startswith("DM-")
    assert len(code) > 5
