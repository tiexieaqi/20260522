MESSAGES={'model_capacity':('AI 模型繁忙','当前 OpenAI 模型服务繁忙，暂时无法处理本项目。','稍后重试。'),'usage_limit_exceeded':('已达到使用额度','当前账户额度不足。','等待额度恢复后再试。'),'provider_timeout':('AI 请求超时','AI 服务没有及时响应。','稍后重试。'),'script_encoding_error':('剧本编码错误','剧本文件无法可靠解码。','转换为 UTF-8 或 GB18030 后重试。'),'script_text_corrupted':('剧本文本损坏','剧本包含无法可靠读取的字符。','检查剧本文件后重试。'),'source_mismatch':('源剧本已变化','源剧本已变化，不能从旧断点继续。','重新创建项目。'),'stale_output':('项目输出过期','发现旧输出。','重新运行当前阶段。')}
def explain(code,message='',stage=None):
    title,detail,action=MESSAGES.get(code,('项目运行失败',message or '发生未知错误。','查看技术详情。'))
    return {'title':title,'user_message':detail,'action':action,'technical':{'error_type':code,'stage':stage,'message':message}}
