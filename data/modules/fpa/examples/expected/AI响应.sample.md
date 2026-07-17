<AI评估.md>
# 在线理赔影像补传与状态通知 FPA 评估

## 需求理解
本次需求是在在线理赔服务平台中支持用户补传事故影像、维护补传记录、推送审核状态，并在案件资料页展示补传影像和审核状态。

## 使用的系统资料
已使用 teamtools-system-brief.md 作为系统简述。本样例未使用 08-FPA场景拆分字典.md，因此进入无系统字典模式。

## 无系统字典模式说明
由于缺少 08-FPA场景拆分字典.md，模块、计数项名称和系统场景编号按系统简述与通用 FPA 路由规则临时归类，需业务人员复核。

## 功能点拆分过程摘要
先提取 F-001 至 F-003 三条变更事实，再路由到 R03、R01、R06、R05，最后冻结为 FP-001 至 FP-004 四条功能点。

## 关键假设
影像补传记录由在线理赔服务平台维护，审核状态通知属于带业务判断结果的输出，查询展示不包含复杂派生计算。

## 目标人天校准说明
目标人天仅作为复用程度和待复核点解释参考，未改变功能点数量、拆分边界或合并边界。

## 最终功能点摘要
最终冻结 ILF 1 条、EI 1 条、EO 1 条、EQ 1 条，共 4 条功能点；无 EIF。

## 待复核点
需复核缺少系统 08 字典时的模块归属、计数项名称，以及补传记录是否已有可复用逻辑数据组。
</AI评估.md>

<AI结构化结果.json>
{
  "schema_version": "fpa.ai_contract.v2",
  "requirement_name": "在线理赔影像补传与状态通知",
  "assessment_context": {
    "system_code": "onlineclaim",
    "system_name": "在线理赔服务平台",
    "system_type": "多流程支持系统",
    "source_level": "L2",
    "requirement_level": "D3",
    "estimation_mode": "早期估算",
    "has_system_knowledge": true,
    "has_system_scene_dictionary": false,
    "no_system_dictionary_mode": true,
    "target_person_days_provided": true,
    "target_calibration_policy": "目标人天仅用于解释复用程度和待复核点，不改变功能点数量、拆分边界或合并边界。",
    "dictionary_gap_note": "系统资料包缺少 08-FPA场景拆分字典.md，本次按系统简述和通用 FPA 规则临时归类。"
  },
  "project_features": {
    "规模计数时机": "估算中期",
    "完整性级别": "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式"
  },
  "change_facts": [
    {
      "fact_id": "F-001",
      "business_purpose": "支持理赔用户补传事故影像并纳入案件资料。",
      "trigger": "用户在在线理赔流程中提交补传影像。",
      "input": "案件号、影像文件、影像类型、补传说明。",
      "processing": "校验案件状态和影像格式，将补传记录关联到案件资料。",
      "output": "补传提交结果。",
      "maintained_data": "案件影像补传记录。",
      "referenced_data": "案件基础信息、影像类型配置。",
      "evidence": "需求第 1-2 条。",
      "in_scope": true
    },
    {
      "fact_id": "F-002",
      "business_purpose": "向用户反馈补传资料审核状态。",
      "trigger": "补传资料审核完成。",
      "input": "审核结论和案件号。",
      "processing": "生成审核结果通知并推送给用户。",
      "output": "审核状态通知。",
      "maintained_data": "",
      "referenced_data": "案件影像补传记录。",
      "evidence": "需求第 3 条。",
      "in_scope": true
    },
    {
      "fact_id": "F-003",
      "business_purpose": "支持用户查询已补传影像和审核状态。",
      "trigger": "用户打开案件资料页面。",
      "input": "案件号。",
      "processing": "读取案件影像补传记录并展示状态。",
      "output": "补传影像列表和审核状态。",
      "maintained_data": "",
      "referenced_data": "案件影像补传记录。",
      "evidence": "需求第 4 条。",
      "in_scope": true
    }
  ],
  "routing_decisions": [
    {
      "route_id": "R-001",
      "fact_ids": [
        "F-001"
      ],
      "route_code": "R03",
      "route_name": "外部用户提交业务资料",
      "candidate_category": "EI",
      "decision": "计数",
      "system_scene_ids": [],
      "rationale": "用户补传影像会维护案件影像补传记录，符合外部输入 EI。"
    },
    {
      "route_id": "R-002",
      "fact_ids": [
        "F-001"
      ],
      "route_code": "R01",
      "route_name": "内部逻辑数据维护",
      "candidate_category": "ILF",
      "decision": "计数",
      "system_scene_ids": [],
      "rationale": "案件影像补传记录由本系统维护，有独立业务含义，作为 ILF 候选。"
    },
    {
      "route_id": "R-003",
      "fact_ids": [
        "F-002"
      ],
      "route_code": "R06",
      "route_name": "派生输出或通知",
      "candidate_category": "EO",
      "decision": "计数",
      "system_scene_ids": [],
      "rationale": "审核状态通知包含业务判断结果并输出给用户，按 EO 处理。"
    },
    {
      "route_id": "R-004",
      "fact_ids": [
        "F-003"
      ],
      "route_code": "R05",
      "route_name": "查询展示",
      "candidate_category": "EQ",
      "decision": "计数",
      "system_scene_ids": [],
      "rationale": "查询补传影像和状态，以读取展示为主，按 EQ 处理。"
    }
  ],
  "split_merge_decisions": [
    {
      "decision_id": "D-001",
      "route_ids": [
        "R-001"
      ],
      "decision": "拆分",
      "result_stable_ids": [
        "FP-001"
      ],
      "rationale": "补传提交是独立用户触发的维护过程，应单独冻结。"
    },
    {
      "decision_id": "D-002",
      "route_ids": [
        "R-002"
      ],
      "decision": "拆分",
      "result_stable_ids": [
        "FP-002"
      ],
      "rationale": "补传记录是独立逻辑数据组，应单独冻结。"
    },
    {
      "decision_id": "D-003",
      "route_ids": [
        "R-003"
      ],
      "decision": "拆分",
      "result_stable_ids": [
        "FP-003"
      ],
      "rationale": "审核状态通知是独立输出过程，应单独冻结。"
    },
    {
      "decision_id": "D-004",
      "route_ids": [
        "R-004"
      ],
      "decision": "拆分",
      "result_stable_ids": [
        "FP-004"
      ],
      "rationale": "查询展示是独立查询过程，应单独冻结。"
    }
  ],
  "frozen_items": [
    {
      "stable_id": "FP-001",
      "system": "在线理赔服务平台",
      "level1_module": "理赔服务",
      "level2_module": "影像资料",
      "level3_module": "",
      "level4_module": "",
      "function_description": "用户补传事故影像并提交案件资料。",
      "count_item_name": "影像补传提交",
      "category": "EI",
      "reuse": "中",
      "change_type": "新增",
      "remark": "外部用户提交并维护补传记录，按 EI；基于现有理赔流程扩展，复用中；新增资料提交能力。",
      "fact_ids": [
        "F-001"
      ],
      "route_ids": [
        "R-001"
      ],
      "system_scene_ids": []
    },
    {
      "stable_id": "FP-002",
      "system": "在线理赔服务平台",
      "level1_module": "理赔服务",
      "level2_module": "影像资料",
      "level3_module": "",
      "level4_module": "",
      "function_description": "维护案件影像补传记录。",
      "count_item_name": "影像补传记录",
      "category": "ILF",
      "reuse": "中",
      "change_type": "新增",
      "remark": "由本系统维护的逻辑数据组，按 ILF；依托既有案件资料能力，复用中；新增补传记录。",
      "fact_ids": [
        "F-001"
      ],
      "route_ids": [
        "R-002"
      ],
      "system_scene_ids": []
    },
    {
      "stable_id": "FP-003",
      "system": "在线理赔服务平台",
      "level1_module": "理赔服务",
      "level2_module": "消息通知",
      "level3_module": "",
      "level4_module": "",
      "function_description": "向用户推送补传资料审核状态。",
      "count_item_name": "补传审核通知",
      "category": "EO",
      "reuse": "中",
      "change_type": "新增",
      "remark": "通知包含审核结论等派生信息，按 EO；复用现有消息能力，复用中；新增通知场景。",
      "fact_ids": [
        "F-002"
      ],
      "route_ids": [
        "R-003"
      ],
      "system_scene_ids": []
    },
    {
      "stable_id": "FP-004",
      "system": "在线理赔服务平台",
      "level1_module": "理赔服务",
      "level2_module": "影像资料",
      "level3_module": "",
      "level4_module": "",
      "function_description": "查询案件已补传影像和审核状态。",
      "count_item_name": "补传影像查询",
      "category": "EQ",
      "reuse": "中",
      "change_type": "新增",
      "remark": "读取并展示补传记录，不含复杂派生计算，按 EQ；复用既有案件资料页，复用中；新增查询内容。",
      "fact_ids": [
        "F-003"
      ],
      "route_ids": [
        "R-004"
      ],
      "system_scene_ids": []
    }
  ],
  "review_notes": [
    {
      "code": "NO_SYSTEM_SCENE_DICTIONARY",
      "message": "系统资料包缺少 08-FPA场景拆分字典.md，模块和计数项名称需要业务人员复核。",
      "severity": "medium"
    }
  ]
}

</AI结构化结果.json>
