import requests
import json

# Extract cookies from the cURL command
cookies_string = 'bcookie="v=2&d312e7b7-b7b4-41db-8f21-1722c938daf0"; bscookie="v=1&20250923170805e453ee50-a27c-4d65-8809-7eb4d601caceAQHT8kUUOYGCAQGIXaEG3WHum0Pf_y_f"; li_rm=AQGhRPJr5WxwLwAAAZl3i_8Mn2SnQkF4A34j2RKRpWbp-C4QrNJ1pr3KuXy3iTtM1DL80XOFkk3uaiMvZRnm0A20v1ykKxxtJacaKEMVy-jJ_5FMHpWhEg2x; _guid=58fbf2f8-427c-4237-8f66-4ba03db24863; li_sugr=883927fa-1e3a-4546-844d-312fa77ee18a; dfpfpt=394ec22c84a54042a62d91e587813459; visit=v=1&M; sdui_ver=sdui-flagship:0.1.15145-4+sdui-flagship.production; fid=AQEkSXFkCLfp5gAAAZol_aIKu0xC5_D5qCkfeCBi9c-3qXzvxWVRCR6fenLjx1_S-iUtr-z3yVC3TA; g_state={"i_l":0}; timezone=Asia/Calcutta; li_theme=light; li_theme_set=app; AnalyticsSyncHistory=AQJoVn1uPddrQAAAAZol_e0LkiEUyS9btS0nyMLASVObf09N1cBQbsOVbTwSZn2oAdrN-UNDzCsrV7h5uE-FMA; lms_ads=AQHDepTDrxAhwwAAAZol_e4vZdShJ2RtQP_QM6zCBHR8qTbyhrLOR8ddxLL0YzUU4PyWqHkwCybop4-x4JSRLXytXbyT53pz; lms_analytics=AQHDepTDrxAhwwAAAZol_e4vZdShJ2RtQP_QM6zCBHR8qTbyhrLOR8ddxLL0YzUU4PyWqHkwCybop4-x4JSRLXytXbyT53pz; gpv_pn=developer.linkedin.com%2F; s_ips=967; _uetsid=61849020b3c611f09d3563b6c9756439; _uetvid=4d26b6109b5911f0950db9a49dcae326; mbox=session#4624d63ea811449bbb650ab0bf24900c#1761634376|PC#4624d63ea811449bbb650ab0bf24900c.41_0#1777184516; s_tp=3048; s_tslv=1761632519101; lang=v=2&lang=en-us; fptctx2=taBcrIH61PuCVH7eNCyH0FFaWZWIHTJWSYlBtG47cVuboIRRg3Xveil8w1fkqdH5MDDdEd4OVwF1MQ6qMqxk49oG9HAc8jWWmR40h5vrmBegy%252b8FvcmtHXylrWFglVkQvrBw3Ieoo0f9wInVZnIi4Ig9191KnTalWnB042LoRI5r%252bOHQxHGtz7lsQKG1ZfKAYOLAxFLKYblYrONENdQfPJ26ojNHPRbbWEUkf9GGABsmrk84Ar4KQ3IgsIwhHQOWviVyHXQ7R38GB38sw8citwEZX%252fO2Rgm0E7WMOlIfoOBNKewZ4n4%252fbcXpoPYmOnVBk4lJyZoE%252bCpk0otc79%252fBdfHBy7EcDFmJNsz887Wz14F%252bSAThuLEwiXsELsNwOIEjFZeJ2kXQ80A%252fcs0AVQ42dw%253d%253d; bitmovin_analytics_uuid=78c2fa4d-6c13-457d-b3eb-7cef85dddf9f; AMCVS_14215E3D5995C57C0A495C55%40AdobeOrg=1; AMCV_14215E3D5995C57C0A495C55%40AdobeOrg=-637568504%7CMCIDTS%7C20389%7CMCMID%7C90911317835115028424505692513845595515%7CMCOPTOUT-1761669219s%7CNONE%7CvVersion%7C5.1.1; li_at=AQEDAWA6xS8Dq8DQAAABmis9O1AAAAGaT0m_UE4Apd4ndhUoehRndLUbS5ysTnSU8E6VLBKDgGOuxsdiJa9wU8FTj8iISYWj1TSgTUy6K2XfR6vYWu-6lF7sdx_vjjKknMr5Gk0vq883LR7PXDtjd8vC; liap=true; JSESSIONID="ajax:8343742463670370208"; lidc="b=OB03:s=O:r=O:a=O:p=O:g=6802:u=4:x=1:i=1761667852:t=1761754071:v=2:sig=AQHstUK73DaMcvkqIeCFnxApnlE544fn"; UserMatchHistory=AQILiukcYOFlAwAAAZornXf1mlNU_VLohLcmrRKPiMvZ0gsAQb4msBtMRnhhBuCpdbCW-0RTJ7x_9OkYE7ER3hw7BBDiKslrkDEGppyoQNnqKKZoC19iIJB2gXce-YxJKqKYwCqAaM83Im_opF5_mTjofjU2imTyNKP5F3UyNMqxTxuKpJPwp8CZo_TAvbXXC5tnAhbayeGP48QhTLAJotnr1DLco9fBTetj1g0zURdvhCZhmCgjmbtUxVMQnnKJBtN3BsHwrru1A9aoXlGy50xOQPuNgO5AV4DO6RdOKHFSzzYfl2IeW2WBt9-pFZjn0tEfeD_nQnRA4k9PVxvA_FkrMusMykA3s1jBIV7-hicBfj57GQ'

# Parse cookies into dictionary format
cookies = {}
for cookie_pair in cookies_string.split('; '):
    if '=' in cookie_pair:
        key, value = cookie_pair.split('=', 1)
        # Remove quotes if present
        value = value.strip('"')
        cookies[key] = value

# The exact URL from your cURL
url = 'https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(count:20,start:0,profileUrn:urn%3Ali%3Afsd_profile%3AACoAAC6Afp8BG1UgRMngvimZEGua_jE15LFwy9I)&queryId=voyagerFeedDashProfileUpdates.4af00b28d60ed0f1488018948daad822'

# Headers from your cURL command
headers = {
    'accept': 'application/vnd.linkedin.normalized+json+2.1',
    'accept-language': 'en-US,en;q=0.8',
    'cache-control': 'no-cache',
    'csrf-token': 'ajax:8343742463670370208',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.linkedin.com/in/chriskempczinski/recent-activity/all/',
    'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    'x-li-lang': 'en_US',
    'x-li-page-instance': 'urn:li:page:d_flagship3_profile_view_base_recent_activity_content_view;SA/+879cR+OuXzx9RGjcFQ==',
    'x-li-track': '{"clientVersion":"1.13.40128","mpVersion":"1.13.40128","osName":"web","timezoneOffset":5.5,"timezone":"Asia/Calcutta","deviceFormFactor":"DESKTOP","mpName":"voyager-web","displayDensity":1,"displayWidth":1680,"displayHeight":1050}',
    'x-restli-protocol-version': '2.0.0'
}

# Make the request
response = requests.get(url, headers=headers, cookies=cookies)

print(f"Status Code: {response.status_code}")

try:
    response_json = response.json()
    # Save JSON response to file
    with open('linkedin_profile_activity.json', 'w', encoding='utf-8') as f:
        json.dump(response_json, f, ensure_ascii=False, indent=2)
    print("Response saved to linkedin_profile_activity.json")
except Exception as e:
    print(f"Error parsing JSON: {e}")
    # Save raw text in case JSON parsing fails
    with open('linkedin_profile_activity_raw.txt', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("Raw response saved to linkedin_profile_activity_raw.txt")