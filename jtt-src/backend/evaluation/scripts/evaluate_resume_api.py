"""通过运行中的 JTT API 评测 PDF/DOCX 简历解析结果。"""
import argparse, asyncio, json
from pathlib import Path
import httpx
from common import load_json, normalized, set_value, write_json

async def run(args):
    root = Path(__file__).resolve().parents[2]
    gold = load_json(root / args.gold).get('items', [])
    headers = {'Authorization': f'Bearer {args.token}'} if args.token else {}
    results = []
    semaphore = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.timeout, headers=headers) as client:
        async def evaluate_one(item):
            path = root / args.resume_dir / item['file_name']
            try:
                async with semaphore:
                    content = path.read_bytes()
                    response = await client.post('/api/v1/resume/upload', files={'file': (path.name, content, 'application/octet-stream')})
                body = response.json()
                data = body.get('data') or {}
                resume = data.get('resume') or {}
                actual = set_value(data.get('extracted_skills') or [x.get('name') for x in resume.get('skills', [])])
                expected = set_value(item.get('expected_skills'))
                tp = len(actual & expected)
                if not actual and not expected:
                    precision = recall = f1 = 1.0
                else:
                    precision = tp / len(actual) if actual else 0
                    recall = tp / len(expected) if expected else 0
                    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
                return {'id': item['id'], 'file_name': path.name, 'status_code': response.status_code, 'skill_f1': f1, 'parse_accuracy': data.get('parse_accuracy'), 'actual_skills': sorted(actual), 'expected_skills': sorted(expected)}
            except Exception as exc:
                return {'id': item['id'], 'file_name': path.name, 'status': 'error', 'error': f'{type(exc).__name__}: {exc}'}
        results = await asyncio.gather(*(evaluate_one(item) for item in gold))
    valid = [x for x in results if x.get('status_code') == 200 and 'skill_f1' in x]
    report = {'status': 'ready' if valid else 'pending_auth_or_failed', 'sample_count': len(results), 'valid_count': len(valid), 'http_success_rate': len(valid) / len(results) if results else 0, 'skill_f1': sum(x['skill_f1'] for x in valid) / len(valid) if valid else None, 'items': results}
    write_json(root / args.output, report); print(json.dumps(report, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--base-url', default='http://127.0.0.1:8001'); parser.add_argument('--token', default=''); parser.add_argument('--gold', default='evaluation/datasets/resume_gold.json'); parser.add_argument('--resume-dir', default='evaluation/private_resume'); parser.add_argument('--output', default='evaluation/reports/resume_api_accuracy.json'); parser.add_argument('--timeout', type=float, default=120); parser.add_argument('--concurrency', type=int, default=3); args = parser.parse_args(); asyncio.run(run(args))

if __name__ == '__main__': main()
