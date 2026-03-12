import requests, json
APPID = 'wxee39faecaca1df63'
SECRET = '8d2d07dba9581f30f6774482e2f38e1b'
token_url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}'
access_token = requests.get(token_url).json()['access_token']

html1 = '<ol><li>Apple</li><li>Banana</li></ol><br>'
html2 = '<ol><li><p>Apple</p></li><li><p>Banana</p></li></ol><br>'
html3 = '<ol><li style="margin-bottom: 6px;">Apple</li><li style="margin-bottom: 6px;">Banana</li></ol><br>'

payload = {
    'articles': [{
        'title': 'Test Lists',
        'content': html1 + html2 + html3,
        'thumb_media_id': 'n_azzRwlk5Vzss6Nl04Vr9hUP0B-c2MD8u93R4rDvlM_XRJBGbJ74Z4PedH_CaB0',
    }]
}
res = requests.post(f'https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}', data=json.dumps(payload, ensure_ascii=False).encode('utf-8')).json()
print('Draft created:', res)
