ARTIFACTS={1:['01_剧本解析报告.md'],2:['02_项目专属规则.md'],3:['03_资产库.md','assets.json'],4:['04_资产生成提示词.md','asset_prompts.json'],5:['05_标准分镜.md','storyboard.json'],6:['06_Seedance2.0提示词.md','seedance20_prompts.json'],7:['07_Seedance2.5提示词.md','seedance25_prompts.json'],8:['08_即梦2.0提示词.md','jimeng20_prompts.json'],9:['09_即梦2.5提示词.md','jimeng25_prompts.json'],10:['10_连续性审核报告.md','continuity_report.json'],11:['11_历史真实性审核报告.md','historical_report.json'],12:['12_AI生成风险报告.md','generation_risk_report.json']}
def check_upstream(project,stage):
 for n in ARTIFACTS.get(stage-1,[]):
  if not (project/n).is_file(): return {'ok':False,'error_type':'upstream_output_missing','missing_stage':stage-1,'missing_artifact':n,'recommended_restart_stage':stage-1}
 return {'ok':True}
