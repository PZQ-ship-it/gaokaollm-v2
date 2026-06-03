一、 推荐决策层（算法层）：重写帕累托候选对构造公式当前论文的 2.3.2 节公式 (2-20) 是通过最大化 $L_1$ 散度来寻找挑战者方案 $B_t$。为了解决“诱惑力不够”和“旁支特征混杂”的问题，我们需要将简单的散度最大化，改为“带噪声惩罚的收益极大化”约束寻优。  论文公式 (2-20) 优化方案：设本轮 UCB 选定的测试目标维度为 $k_{target}$（如学费），预期补偿收益维度为 $k_{gain}$（如学校层次），其余为旁支维度集合 $K_{others}$。$$B_t = \arg\max_{x\in\mathcal{C}_{hard}} \phi_{gain}(x) \tag{2-20a}$$$$s.t. \quad \phi_{target}(x) - \phi_{target}(A_t) \le -\epsilon_{loss} \tag{2-20b}$$$$\sum_{j \in K_{others}} |\phi_j(x) - \phi_j(A_t)| \le \tau_{noise} \tag{2-20c}$$逻辑自洽：公式 (2-20a) 保证了系统总是抛出“极值诱惑”（比如尽全力找一所层次最高的双非）；公式 (2-20c) 引入了 $\tau_{noise}$ 阈值，严格限制了专业、地域等旁支维度的漂移。这在底层物理算力上，最大程度保证了探针的“强诱惑”与“纯净度”。

核心代码实现：probers.py 优化模块
假设你已经从数据库中拉取了当前可行域内的候选列表 available_candidates，并且选定了基准方案 candidate_A。

Python
import numpy as np
from typing import List, Dict, Optional

def select_maximum_contrast_candidate(
    candidate_A: Dict,
    available_candidates: List[Dict],
    target_dim: str,          # 本轮试图放宽/试探的维度 (如: tuition)
    gain_dim: str,            # 用于诱惑用户的收益维度 (如: school_tier)
    epsilon_loss: float = 0.1, # 目标维度要求的最小张力差值 (归一化尺度)
    initial_tau: float = 0.05, # 初始旁支噪声容忍度
    max_tau: float = 0.30,     # 最大允许的旁支噪声阈值
    tau_step: float = 0.05     # 每次退避放宽的步长
) -> Optional[Dict]:
    """
    基于最大张力与最小混杂的挑战者方案寻优 (对齐公式 2-20 改良版)
    """
    best_candidate = None
    max_gain = -float('inf')
    
    # 定义所有 6 个连续特征维度，并剥离出旁支维度集合 K_others
    all_dims = ["school_tier", "major_match", "tuition", "quality", "geo", "risk"]
    other_dims = [dim for dim in all_dims if dim not in (target_dim, gain_dim)]
    
    current_tau = initial_tau
    
    # 动态阈值退避循环：如果在当前极严的噪声限制下找不到解，则逐步放宽噪声阈值
    while current_tau <= max_tau and best_candidate is None:
        
        for cand in available_candidates:
            # 排除自身或相同的实体
            if cand["id"] == candidate_A["id"]:
                continue
                
            features_A = candidate_A["features"]
            features_cand = cand["features"]

            # ==========================================
            # 1. 检验约束 (公式 2-20b)：试探张力必须足够大
            # ==========================================
            # 假设特征已归一化，且 target_dim 是越大约好（如果是越小越好，如学费，需取反或统一绝对值）
            # 这里以统一效用得分为例：新方案在目标维度上的效用必须比 A 显著下降
            target_diff = features_cand[target_dim] - features_A[target_dim]
            if target_diff > -epsilon_loss: 
                continue  # 牺牲不够痛，没有试探价值，跳过
            
            # ==========================================
            # 2. 检验约束 (公式 2-20c)：旁支特征混杂必须小于阈值
            # ==========================================
            # 计算专业、地域、风险等非目标轴的 L1 散度总和
            noise_sum = sum(abs(features_cand[dim] - features_A[dim]) for dim in other_dims)
            if noise_sum > current_tau:
                continue  # 旁支差异太大，构成严重混杂变量，跳过
            
            # ==========================================
            # 3. 寻优目标 (公式 2-20a)：最大化预期收益
            # ==========================================
            gain_val = features_cand[gain_dim]
            if gain_val > max_gain:
                max_gain = gain_val
                best_candidate = cand
                # 记录本轮实际产生的混杂残差，用于后续 UI 动态归因拦截
                best_candidate["residual_noise"] = noise_sum 
        
        # 如果遍历完一圈依然找不到候选者，说明条件过于苛刻，放宽旁支噪声限制
        if best_candidate is None:
            current_tau += tau_step

    return best_candidate


二、 智能体服务层（工作流层）：扩充 AgentState 契约在 3.4.2 运行时状态机与通信协议 中，AgentState 是节点间通信的唯一契约。为了支持“态度走物理按键，归因走 LLM 抽取”的双轨制，状态机必须增加对“用户补充文本”和“动态条件约束”的承载。  修改 AgentState 定义：Pythonclass AgentState(TypedDict):
    # ... [保留原有的 implicit_weights, candidates 等] ...
    
    # 1. 承载用户在前端 UI 补充的自然语言（如果只点了拒绝，则为空）
    user_supplementary_text: str 
    
    # 2. 承载大模型抽取出的符号化条件约束（追加到原有 factual_blocked_dimensions 之上）
    # 数据结构示例: [{"axis": "major", "operator": "IN", "value": ["计算机大类"]}]
    conditional_constraints: List[Dict[str, Any]] 
三、 状态机流转层：LangGraph preference_tracker 节点重构这部分对应论文 3.4 智能体工作流与运行时状态机 的图 3.7。在 interrupt/resume 唤醒状态图后，偏好后验追踪器（Preference Tracker）需要执行一个漂亮的分流判定。  伪代码实现与论文对齐逻辑：Pythondef preference_tracker_node(state: AgentState) -> AgentState:
    feedback_signal = state["last_feedback_type"] # 明确的 ACCEPT/REJECT/HESITATE
    supplementary_text = state.get("user_supplementary_text", "").strip()
    
    # 获取当前状态
    w_t = np.array(state["implicit_weights"])
    v_t = np.array(state["cognitive_variance"])
    delta_phi = np.array(state["current_probe_pair"]["delta_phi"])
    
    new_constraints = []

    # ==========================================
    # 核心分流：判断是否存在“条件归因”
    # ==========================================
    if feedback_signal == "REJECT" and supplementary_text != "":
        # 路径 B：用户填写了拒绝理由（觉得诱惑不够，或者旁支特征不匹配）
        # 1. 【梯度物理冻结】：彻底阻断 Bradley-Terry 计算
        w_next, v_next = w_t, v_t 
        
        # 2. 【LLM 符号提取】：调用大模型扮演 NER 角色
        extraction_prompt = f"""
        本轮系统试图放宽 {state['ucb_target_dimension']} 维度。
        但用户给出了特定的拒绝条件："{supplementary_text}"。
        请提取出不可妥协的底线，返回 JSON，包含轴(axis)与强制要求(value)。
        """
        extracted_json = llm.predict_json(extraction_prompt)
        new_constraints.append(extracted_json)
        
    else:
        # 路径 A：用户纯粹通过按钮表达态度（接受 / 纯净的拒绝 / 犹豫）
        # 执行论文 2.3.3 和 2.3.4 的原生数学更新
        w_next, v_next = preference_engine.update_state(w_t, v_t, delta_phi, feedback_signal)

    # 汇总并流转状态
    updated_constraints = state.get("conditional_constraints", []) + new_constraints
    
    return {
        "implicit_weights": w_next.tolist(),
        "cognitive_variance": v_next.tolist(),
        "conditional_constraints": updated_constraints
    }
四、 数据证据层（底层查询层）：动态 SQL 条件拼接在论文的 3.3 数据层构建与证据底座 中，确定性证据探针（SQL）是保证零幻觉的最后防线。上一层 conditional_constraints 里收集到的所有大模型提取规则，必须在这里转化为生硬的 WHERE 子句。  在 probers.py 中的修改：Pythondef build_candidate_query(base_constraints, conditional_constraints):
    sql_query = "SELECT * FROM admission_facts WHERE 1=1"
    params = []
    
    # 1. 挂载显式硬约束（分数、省份等）
    # ... (原有逻辑) ...
    
    # 2. 挂载双轨制交互中提取的“动态条件约束”
    for cond in conditional_constraints:
        if cond["axis"] == "major":
            # 例如用户补充了：“除非是计算机我才去”
            sql_query += " AND major_category = %s"
            params.append(cond["value"])
        elif cond["axis"] == "school_tier":
            # 例如用户补充了：“底线是公办”
            sql_query += " AND is_public = true"
            
    return sql_query, params