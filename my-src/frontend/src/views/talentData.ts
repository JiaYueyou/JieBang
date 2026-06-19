export interface TalentItem {
  id: number;
  name: string;
  position: string;
  score: number;
  isNew: boolean;
  experience: string;
  education: string;
  department: string;
  matched: string[];
  missing: string[];
  targetJobs: string[];
  resumeFile?: string;
  uploadDate?: string;
  urgent?: boolean;
}

export const talentPool: TalentItem[] = [
  { id: 1, name: "李思远", position: "Java 高级开发", score: 92, isNew: true, experience: "5 年", education: "本科", department: "后台开发组", matched: ["Java","Spring Boot","MySQL","Redis","微服务","MyBatis"], missing: ["K8s","Docker"], targetJobs: ["Java 高级开发","系统架构师"], resumeFile: "李思远_Java开发_5年.pdf", urgent: true },
  { id: 2, name: "王语晴", position: "Python 后端开发", score: 89, isNew: true, experience: "3 年", education: "硕士", department: "数据平台组", matched: ["Python","Django","PostgreSQL","Linux","Docker"], missing: ["FastAPI","Redis"], targetJobs: ["Python 后端开发"], resumeFile: "王语晴_Python_3年.pdf", urgent: false },
  { id: 3, name: "赵明哲", position: "AI 算法工程师", score: 87, isNew: true, experience: "4 年", education: "硕士", department: "AI 研究院", matched: ["Python","PyTorch","TensorFlow","NLP","Transformer"], missing: ["大模型部署","CUDA"], targetJobs: ["AI 算法工程师","NLP 工程师"], resumeFile: "赵明哲_AI算法_4年.pdf", urgent: true },
  { id: 4, name: "陈晓雯", position: "前端开发工程师", score: 85, isNew: false, experience: "3 年", education: "本科", department: "前端开发组", matched: ["Vue","TypeScript","Element Plus","HTML/CSS"], missing: ["React","Node.js"], targetJobs: ["前端开发工程师","全栈开发"], urgent: false },
  { id: 5, name: "刘志强", position: "Java 高级开发", score: 83, isNew: false, experience: "6 年", education: "大专", department: "后台开发组", matched: ["Java","Spring Cloud","Oracle","MyBatis","JPA"], missing: ["微服务","K8s","Redis"], targetJobs: ["Java 高级开发"], urgent: false },
  { id: 6, name: "孙晓琳", position: "DevOps 工程师", score: 81, isNew: false, experience: "4 年", education: "本科", department: "运维组", matched: ["Docker","K8s","Jenkins","Linux","Shell"], missing: ["Terraform","Ansible"], targetJobs: ["DevOps 工程师","SRE"], resumeFile: "孙晓琳_DevOps_4年.pdf", urgent: true },
  { id: 7, name: "周明辉", position: "大数据工程师", score: 78, isNew: false, experience: "5 年", education: "硕士", department: "数据平台组", matched: ["Spark","Hadoop","Hive","Python","SQL"], missing: ["Flink","Kafka"], targetJobs: ["大数据工程师"], urgent: false },
  { id: 8, name: "吴佳琪", position: "软件测试工程师", score: 76, isNew: false, experience: "3 年", education: "本科", department: "测试组", matched: ["Selenium","JMeter","Python","SQL"], missing: ["性能测试","自动化框架设计"], targetJobs: ["软件测试工程师","测试开发"], urgent: false },
];
