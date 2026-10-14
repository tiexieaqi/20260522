# 05 Seedance 2.0 提示词模板

## 模板标识

- template_id：SEEDANCE_2_0_PROMPT_V1
- template_version：1.0

## 输入字段

| 字段键 | 必填 | 说明 |
|---|---:|---|
| shot_id | 是 | 镜头编号 |
| asset_refs | 是 | CH/LOC/PROP/WPN/GRP 引用 |
| subject | 是 | 主体 |
| action | 是 | 单一主动作 |
| shot_language | 是 | 景别、焦段、机位、运镜 |
| lighting_and_mood | 否 | 光线与情绪 |
| duration_sec | 是 | 时长 |
| continuity | 是 | 连续性约束 |
| negative_constraints | 是 | 禁止项 |

## 处理逻辑

按“资产锚点→主体→动作→场景→镜头→光线情绪→时长→连续性→禁止项”组装；删除互相冲突的动作和运镜；复杂镜头拆分。

## 输出格式

| 字段键 | 输出内容 |
|---|---|
| shot_id | 镜头编号 |
| model | Seedance 2.0 |
| prompt | 完整正向提示词 |
| negative_prompt | 无字幕、无logo、无水印及镜头专属禁用项 |
| asset_refs | 资产 ID 列表 |
| duration_sec | 时长 |
| unresolved_items | 待确认项 |
