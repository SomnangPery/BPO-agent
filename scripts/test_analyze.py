import requests

if __name__ == '__main__':
    try:
        resp = requests.post('http://127.0.0.1:5000/api/analyze_student', json={'student_id': 1}, timeout=120)
        print('STATUS:', resp.status_code)
        print(resp.text)
    except Exception as e:
        print('ERROR:', e)
