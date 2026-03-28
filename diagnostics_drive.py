from ic_agent.drive import _get_drive_service

if __name__ == '__main__':
    s = _get_drive_service()
    r = s.files().list(pageSize=10, fields='files(id,name)').execute()
    files = r.get('files', [])
    print('TOTAL:', len(files))
    for f in files:
        fid = f.get('id')
        print(fid, f.get('name'))
        try:
            meta = s.files().get(fileId=fid, fields='id,name,parents', supportsAllDrives=True).execute()
            print('  parents:', meta.get('parents'))
        except Exception as exc:
            print('  failed to get parents:', exc)
