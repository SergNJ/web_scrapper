import webbrowser
import requests as req
import bs4
import os
import pandas as pd
import pathlib
import shutil
from urllib.parse import urlparse
import re

start_url = 'https://finance.yahoo.com/'

tout = 1.5  # timeout in seconds
download = {  # 'resource type' : [HTML tag to look for, attribute in the tag, download to HDD, exemption substrings]
    'hlink': ['a', 'href', False, ['.zip', '.pdf']],
    'image': ['img', 'src', True, []]
}
min_size = 1024  # minimal size of resource to save on PC

filter_OFF = False  # all URLs included w/o filtering
skip_urls = ['amazon', 'google', 'paypal', 'youtube', 'twitter', 'instagram', '.ad',
             'linkedin', 'facebook']  # filter URLs

file_ext = {'text/html': '.html',  # file extensions for saving to PC depends on HTTP content
            'image/jpeg': '.jpeg',
            'image/png': '.png',
            'image/gif': '.gif',
            'application/zip': '.zip',
            'text/html; charset=UTF-8': '.html',
            'image/svg+xml': '.svg'}

chunk_size = 1024 * 64  # byte chunks for saving to HDD


def filter_url(parsed_url):
    # filter resources
    for domain in skip_urls:
        if domain in parsed_url.netloc:
            return False
    return True


def download_res(res_cnt, url, data_frame, res_type='Unknown', save=False):
    # downloads, lists, and saves resource to PC
    download_status = 'OK'
    try:
        res = req.get(url, timeout=tout)
    except req.exceptions.Timeout as err:
        download_status = 'Skipped. Timeout.'
    except req.exceptions.ConnectionError as err:
        download_status = 'Skipped. Connection error.'
    except req.exceptions.RequestException as err:
        download_status = 'Skipped. Something went wrong.'
    print('Download resource: {:>7}, type: {:>7}, address:{:<} ...{}'.format(res_cnt, res_type, url, download_status))

    if download_status == 'OK':
        parsed_url = urlparse(url)

        if res.headers.get('content-type') in file_ext:
            ext = file_ext[res.headers.get('content-type')]
        else:
            ext = ''

        file_name = parsed_url.netloc + '_' + str(res_cnt) + ext

        if len(res.text) <= min_size:
            file_name = 'too small to save'

        data_frame.loc[len(data_frame.index)] = [url, file_name, res_type, download_status, res.status_code,
                                                 len(res.text), res.headers.get('content-type')]

        if save and len(res.text) >= min_size:
            with open(path + '\\' + file_name, 'wb') as f:
                for chunk in res.iter_content(chunk_size):
                    f.write(chunk)

        return res, len(res.text)

    else:
        data_frame.loc[len(data_frame.index)] = [url, 'failure to download', res_type, download_status, '', 0, '']
        return None, 0


def list_res_only(res_cnt, url, data_frame, res_type):
    # just lists resource without saving to PC
    print('Listed resource: {:>7}, type: {:>7}, address:{:<} ...OK'.format(res_cnt, res_type, url))
    data_frame.loc[len(data_frame.index)] = [url, 'not saved to PC', res_type, 'list only', '', 0, '']


def res_exempt(url, exemptions):
    # checks if URL contains any exemption substrings. If found - then resource has to be downloaded
    for ex in exemptions:
        if ex in url:
            return True
    return False


df = pd.DataFrame({
    'url': ['TOTAL: '],
    'filename': [''],
    'res_type': [''],
    'download_status': [''],
    'HTTP_status': [''],
    'size_bytes': [0],
    'content_type': ['']})

path = str(pathlib.Path.cwd()) + '\\downloaded_' + re.sub('[^\w\-_\. ]', '_', urlparse(start_url).netloc) + '\\'
if os.path.exists(path):
    shutil.rmtree(path)
os.makedirs(path)

res_count = 1
res, bytes_down = download_res(res_cnt=res_count, url=start_url, data_frame=df, res_type='hlink', save=True)
res_count += 1

soup = bs4.BeautifulSoup(res.text, 'html.parser')
print('- PAGE TITLE: \"%s\" ' % soup.title.get_text())

for r, ra in download.items():
    for item in soup.find_all(ra[0]):
        if ra[1] in item.attrs:

            if '://' in item.get(ra[1]):
                hlink = item.get(ra[1])
            else:
                hlink = start_url + item.get(ra[1])

            if filter_url(urlparse(hlink)) or filter_OFF:
                exmp = res_exempt(hlink, ra[3])
                if ra[2] or exmp: # resource to be downloaded or not downloaded but exempt
                    if exmp:
                        res, b = download_res(res_cnt=res_count, url=hlink, data_frame=df, res_type=r, save=True)
                    else:
                        res, b = download_res(res_cnt=res_count, url=hlink, data_frame=df, res_type=r, save=ra[2])
                    bytes_down += b
                else:
                    list_res_only(res_cnt=res_count, url=hlink, data_frame=df, res_type=r)
                res_count += 1

df.loc[0, 'size_bytes'] = bytes_down
df.to_html(path + '\\report.html')
webbrowser.open(path + 'report.html')
