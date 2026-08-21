# 简历多格式识别评测

## 目标

对照赛题“支持 PDF/Word 等格式简历解析、简历要素抽取准确率不低于 90%”的要求，验证生产代码对 PDF、DOCX、PNG、JPG、JPEG 的文本识别与技能抽取能力。

## 数据与隐私

- `resume_format_cases.json` 包含 10 个 AI/软件/基础设施相关岗位画像及人工标注技能真值。
- 画像参考 5 个公开的开源简历模板、虚构示例或生成式假数据项目；来源 URL、许可证和用途说明均记录在数据文件中。
- 测试件只包含虚构候选人编号，不保存真实姓名、电话、邮箱、住址或原始求职者简历。
- `resume_format_corpus/generated/` 是由标注文本生成的 50 个可直接上传到系统的测试文件，每种格式 10 个。

## 指标口径

- 文本准确率：`1 - CER`。比较前统一大小写，并移除空白和标点。
- Token Recall：期望词元在识别文本中的召回率。
- 技能 Precision / Recall / Micro-F1：生产 `RuleSkillExtractor` 的结果与人工技能集合比较。
- 达标线：总体文本准确率、总体技能 Micro-F1、每种格式技能 Micro-F1 均不低于 90%。

## 运行

在 `fyz-src/backend` 下使用项目指定 Conda 环境：

```powershell
E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe scripts/evaluate_resume_formats.py `
  --artifact-dir evaluation/resume_format_corpus/generated `
  --output evaluation/resume_format_metrics.json
```

输出文件 `resume_format_metrics.json` 包含分格式指标、总体指标、质量门禁和失败明细。退出码为 `0` 表示全部门禁通过。

## 当前结果与边界

本版本在 50 个受控样本上的总体文本准确率为 99.92%，技能 Micro-F1 为 98.77%；各格式技能 Micro-F1 为 98.46%-99.24%，全部通过 90% 门禁。已保留边缘 AI 图片中 `IoT` 漏识别和 `C++` 触发额外 `C` 的失败明细，不以规则掩盖误差。该结果证明格式链路和当前标注样本可正确处理，但不是互联网真实简历总体准确率的无偏估计。正式答辩前应追加扫描噪声、倾斜、低分辨率、复杂双栏、表格、艺术字体和手写批注等压力样本，并由两名标注者独立复核真值。
