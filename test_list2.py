import requests, json
APPID = 'wxee39faecaca1df63'
SECRET = '8d2d07dba9581f30f6774482e2f38e1b'
token_url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}'
access_token = requests.get(token_url).json()['access_token']

media_id = 'n_azzRwlk5Vzss6Nl04VrzvmkzJKrBSm9PIIvVB6KQjyxDSKikH-FEmpa1BYaOOq'

html1 = '<ol><li>Apple</li><li>Banana</li></ol>'
html2 = '<ol><li><p>Apple</p></li><li><p>Banana</p></li></ol>'
html3 = '<ol><li style="margin-bottom: 6px;">Apple</li><li style="margin-bottom: 6px;">Banana</li></ol>'
html4 = '<ol><li><span style="display:block">Apple</span></li><li><span style="display:block">Banana</span></li></ol>'

payload = {
    'articles': [{
        'title': 'Test Lists 2',
        'content': 'Test1' + html1 + 'Test2' + html2 + 'Test3' + html3 + 'Test4' + html4,
        'thumb_media_id': media_id,
    }]
}
res = requests.post(f'https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}', data=json.dumps(payload, ensure_ascii=False).encode('utf-8')).json()
print('Draft created:', res)
