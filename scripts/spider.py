import requests
import jsonpath
import datetime
import json
import jieba
import re
import sys

class Spider():
    def __init__(self):
        self.headers = {
    'Accept': 'application/json',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'EagleEye-TraceID': '1ef7b540-c2f9-48b4-ed9d-511488e30c07',
    'Origin': 'https://iflytek.zhiye.com',
    'Pragma': 'no-cache',
    'Referer': 'https://iflytek.zhiye.com/social/jobs',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'X-Requested-With': 'xmlhttprequest',
    'langType': 'zh_CN',
    'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

        self.total_data = []  # 用来存所有岗位信息

    def get_main_html(self,index):
        self.json_data = {
        'PageIndex': index,
        'PageSize': 20,
        'Category': [
           '1',
        ],
        'KeyWords': '',
        'SpecialType': 0,
        'PortalId': '',
        'DisplayFields': [
            'Category',
            'Kind',
            'LocId',
            'PostDate',
            'ClassificationOne',
            'ClassificationTwo',
            'WorkWeChatQrCode',
        ],
    }
        url = 'https://iflytek.zhiye.com/api/Jobad/GetJobAdPageList'
        response = requests.post(url, headers=self.headers,
                                 json=self.json_data)
        return response.json()

    def get_title(self,res):
        job_list = []
        job_title = jsonpath.jsonpath(res,"$..JobAdName") or []
        job_company = ["科大讯飞"] * len(job_title) or []
        job_city = jsonpath.jsonpath(res,"$..LocNames") or []
        job_salary = jsonpath.jsonpath(res,"$..Salary") or []
        job_responsibilities = jsonpath.jsonpath(res, "$..Duty") or []
        job_requirements = jsonpath.jsonpath(res, "$..Require") or []

        job_jd_text = []
        for duty, req in zip(job_responsibilities, job_requirements):
            duty = duty or ""
            req = req or ""
            duty_with_title = "【工作职责】\n" + duty.strip()
            req_with_title = "【任职资格】\n" + req.strip()
            combined = duty_with_title + "\n\n" + req_with_title
            job_jd_text.append(combined)

        job_experience_list = []
        for req in job_requirements:
            req = req or ""
            experience = self.extract_work_experience(req)
            job_experience_list.append(experience)

        skill_keywords = [
            "Python", "Java", "Spark", "Flink", "LR", "GBDT", "DNN", "CNN", "RNN", "Transformer",
            "LLM", "NLP", "RAG", "Agent", "大模型", "机器学习", "深度学习", "算法", "数据分析",
            "数据挖掘", "大数据", "pipeline", "模型优化", "特征工程", "训练调优", "在线服务",
            "数据探查", "工程化部署", "预训练", "微调", "文本生成", "语义分析"
       ]

        def extract_skills(text, skills_list):
            found_skills = []
            pattern = re.compile(r"(" + "|".join(skills_list) + r")", re.IGNORECASE)
            matches = pattern.findall(text)
            seen = set()
            for skill in matches:
                if skill.lower() not in seen:
                    seen.add(skill.lower())
                    found_skills.append(skill)
            return found_skills

        all_job_text = []
        job_keywords_list = []
        for duty, req in zip(job_responsibilities, job_requirements):
            text = (duty or "") + " " + (req or "")
            all_job_text.append(text)
            skills = extract_skills(text, skill_keywords)
            job_keywords_list.append(skills)

        job_keywords = []
        for keywords in job_keywords_list:
            job_keywords.append(keywords)

        job_education_list = []
        for req in job_requirements:
            req = req or ""
            education = self.extract_education(req)
            job_education_list.append(education)

        job_posted_at = jsonpath.jsonpath(res,"$.Data[*].PostDate") or []
        id_list = jsonpath.jsonpath(res,"$..Id") or []
        job_url = []
        for job_url1 in id_list:
            job_url2 = "https://iflytek.zhiye.com/social/detail?jobAdId=" + str(job_url1)
            job_url.append(job_url2)
        job_source = ["科大讯飞招聘"]* len(job_title) or []
        crawl_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        job_crawled_at = [crawl_time] * len(job_title)

        for i in zip(job_title,job_company, job_city, job_salary, job_experience_list,job_education_list,job_jd_text, job_responsibilities,job_requirements, job_keywords, job_posted_at, job_url, job_source, job_crawled_at):
            dic = {
                "title": i[0],
                "company": i[1],
                "city": i[2],
                "salary": i[3],
                "experience": i[4],
                "education": i[5],
                "jd_text": i[6],
                "duty": i[7],
                "require": i[8],
                "keywords": i[9],
                "post_date": i[10],
                "url": i[11],
                "source": i[12],
                "crawled_at": i[13]
            }
            job_list.append(dic)
        self.total_data.extend(job_list)

    def extract_work_experience(self, text):
        if not text:
            return "经验不限"
        patterns = [
            r"(\d+年及以上)",
            r"(\d+-\d+年)",
            r"(\d+年以上)",
            r"(\d+年)工作经验",
            r"(\d+年)",
            r"应届生",
            r"不限"
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                raw_exp = match.group(1) if match.groups() else match.group()
                if raw_exp == "不限":
                    return "经验不限"
                return raw_exp
        return "经验不限"

    def extract_education(self, text):
        if not text:
            return "学历不限"
        education_levels = [
            "高中", "中专", "大专", "专科", "本科", "学士", "硕士", "研究生", "博士"
        ]
        patterns = [
            r"({})及以上".format("|".join(education_levels)),
            r"({})学历".format("|".join(education_levels)),
            r"({})学位".format("|".join(education_levels)),
            r"({})优先".format("|".join(education_levels)),
            r"({})".format("|".join(education_levels))
        ]
        found_educations = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            found_educations.extend(matches)
        if not found_educations:
            return "学历不限"
        seen = set()
        unique_edu = []
        for edu in found_educations:
            if edu not in seen:
                seen.add(edu)
                unique_edu.append(edu)
        priority = {
            "高中": 1, "中专": 2, "大专": 3, "专科": 3,
            "本科": 4, "学士": 4, "硕士": 5, "研究生": 5, "博士": 6
        }
        unique_edu.sort(key=lambda x: priority.get(x, 0), reverse=True)
        return unique_edu[0]

    def Run(self):
        """单次执行一轮采集，对应页面【立即执行】"""
        print("===== 启动单次爬虫任务（模拟【立即执行】） =====")
        for index in range(0, 11):
            print(f"正在抓取第 {index+1} 页")
            res = self.get_main_html(index)
            self.get_title(res)
        with open('科大讯飞.json', 'w', encoding='utf-8') as f:
            json.dump(self.total_data, f, ensure_ascii=False, indent=4)
        print(f"✅ 本轮爬取完成，共 {len(self.total_data)} 条，保存至 科大讯飞.json")

if __name__ == '__main__':
    spider = Spider()
    spider.Run()