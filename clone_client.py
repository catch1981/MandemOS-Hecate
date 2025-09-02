import argparse
import os
import requests

def _load_endpoints():
    env = os.getenv('CLONE_ENDPOINTS')
    if env:
        return [u.strip() for u in env.split(',') if u.strip()]
    url = os.getenv('CLONE_SERVER_URL', 'http://localhost:5000')
    return [url]


ENDPOINTS = _load_endpoints()
REGISTRY_URL = os.getenv('SERVER_REGISTRY_URL')
CLONE_ID = os.getenv('CLONE_ID', os.uname().nodename)


def _discover_endpoints():
    if not REGISTRY_URL:
        return
    try:
        resp = requests.get(f"{REGISTRY_URL}/list", timeout=5)
        if resp.ok:
            data = resp.json()
            for url in data.get('servers', []):
                if url not in ENDPOINTS:
                    ENDPOINTS.append(url)
    except Exception:
        pass


_discover_endpoints()


def send_message(message: str):
    ok = False
    for url in list(ENDPOINTS):
        try:
            resp = requests.post(f"{url}/send", json={'id': CLONE_ID, 'message': message}, timeout=5)
            if resp.ok:
                ok = True
        except Exception:
            ENDPOINTS.remove(url)
    if ok:
        print('message sent')
    else:
        print('error: unable to send message')


def read_messages():
    texts = []
    for url in list(ENDPOINTS):
        try:
            resp = requests.get(f"{url}/read", timeout=5)
            if resp.ok:
                data = resp.text.strip()
                if data:
                    texts.append(data)
        except Exception:
            ENDPOINTS.remove(url)
    if texts:
        print('\n'.join(texts))
    else:
        print('error: no data')


def remember_fact(fact: str):
    ok = False
    for url in list(ENDPOINTS):
        try:
            resp = requests.post(f"{url}/remember", json={'id': CLONE_ID, 'fact': fact}, timeout=5)
            if resp.ok:
                ok = True
        except Exception:
            ENDPOINTS.remove(url)
    if ok:
        print('fact stored')
    else:
        print('error: unable to store fact')


def get_memories():
    texts = []
    for url in list(ENDPOINTS):
        try:
            resp = requests.get(f"{url}/memories", timeout=5)
            if resp.ok:
                data = resp.text.strip()
                if data:
                    texts.append(data)
        except Exception:
            ENDPOINTS.remove(url)
    if texts:
        print('\n'.join(texts))
    else:
        print('error: no data')


def fetch_task():
    for url in list(ENDPOINTS):
        try:
            resp = requests.get(f"{url}/task/assign", params={'id': CLONE_ID}, timeout=5)
            if resp.ok:
                data = resp.json()
                task = data.get('task')
                print(task if task else '(no task)')
                return
        except Exception:
            ENDPOINTS.remove(url)
    print('error: unable to fetch task')


def queue_task(task: str):
    ok = False
    for url in list(ENDPOINTS):
        try:
            resp = requests.post(f"{url}/task", json={'task': task}, timeout=5)
            if resp.ok:
                ok = True
        except Exception:
            ENDPOINTS.remove(url)
    if ok:
        print('task queued')
    else:
        print('error: unable to queue task')


def read_results():
    lines = []
    for url in list(ENDPOINTS):
        try:
            resp = requests.get(f"{url}/updates", timeout=5)
            if resp.ok:
                data = resp.json()
                results = data.get('results', [])
                if results:
                    lines.extend(results)
        except Exception:
            ENDPOINTS.remove(url)
    if lines:
        print('\n'.join(lines))
    else:
        print('(no results)')


def submit_result(result: str):
    ok = False
    for url in list(ENDPOINTS):
        try:
            resp = requests.post(f"{url}/task/result", json={'id': CLONE_ID, 'result': result}, timeout=5)
            if resp.ok:
                ok = True
        except Exception:
            ENDPOINTS.remove(url)
    if ok:
        print('result stored')
    else:
        print('error: unable to store result')


def main():
    parser = argparse.ArgumentParser(description='Interact with a clone server')
    sub = parser.add_subparsers(dest='cmd')

    send_p = sub.add_parser('send', help='broadcast a message')
    send_p.add_argument('message')

    sub.add_parser('read', help='read all messages')

    remember_p = sub.add_parser('remember', help='store a shared fact')
    remember_p.add_argument('fact')

    sub.add_parser('memories', help='read shared facts')

    sub.add_parser('fetch-task', help='request a queued task')

    queue_p = sub.add_parser('queue-task', help='add a task to the queue')
    queue_p.add_argument('task')

    sub.add_parser('results', help='read completed task results')

    result_p = sub.add_parser('submit-result', help='report task result')
    result_p.add_argument('result')

    args = parser.parse_args()

    if args.cmd == 'send':
        send_message(args.message)
    elif args.cmd == 'read':
        read_messages()
    elif args.cmd == 'remember':
        remember_fact(args.fact)
    elif args.cmd == 'memories':
        get_memories()
    elif args.cmd == 'fetch-task':
        fetch_task()
    elif args.cmd == 'queue-task':
        queue_task(args.task)
    elif args.cmd == 'results':
        read_results()
    elif args.cmd == 'submit-result':
        submit_result(args.result)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
