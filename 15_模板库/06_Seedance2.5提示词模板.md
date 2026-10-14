# 06 Seedance 2.5 提示词模板

## 模板标识

- template_id：SEEDANCE_2_5_PROMPT_V1
- template_version：1.0

## 输入字段

| 字段键 | 必填 | 说明 |
|---|---:|---|
| shot_id | 是 | 镜头编号 |
| asset_refs | 是 | 固定资产与变体 |
| start_state | 是 | 开始状态 |
| action_sequence | 是 | 连续动作阶段 |
| end_state | 是 | 结束状态 |
| camera_instruction | 是 | 景别、焦段、机位和主运镜 |
| duration_sec | 是 | 时长 |
| continuity | 是 | 连续性约束 |
| negative_constraints | 是 | 禁止项 |

## 处理逻辑

将复杂动作整理为“开始—过程—结束”；保留一条主镜头运动；绑定资产变体；删除多主体争焦和时空跳变要求。

## 输出格式

| 字段键 | 输出内容 |
|---|---|
| shot_id | 镜头编号 |
| model | Seedance 2.5 |
| prompt | 连续动作提示词 |
| negative_prompt | 无字幕、无logo、无水印及专属禁用项 |
| asset_refs | 资产与变体 ID |
| duration_sec | 时长 |
| continuity_notes | 连续性说明 |
| unresolved_items | 待确认项 |
