1. 明确反馈：接受 (Accept) 与 拒绝 (Reject)当用户给出明确的倾向时，系统认为获得了高质量的偏好信号，因此主要更新权重期望。期望（权重）更新：系统采用 Bradley-Terry 在线后验追踪机制 。将接受记为 $y_t=1$，拒绝记为 $y_t=0$ 。系统首先计算在当前权重 $w_t$ 下，用户愿意承担代价去选择妥协方案 $B$ 的概率：
  $$P_t(B) = \frac{1}{1 + \exp(-\tau w_t^\top \Delta\Phi_t)}$$
随后，执行逻辑斯蒂梯度上升（Logistic Gradient Ascent）来修正权重的期望均值：
  $$\tilde{w}_{t+1} = w_t + \eta\tau(y_t - P_t(B))\Delta\Phi_t$$
机制本质：如果用户接受了方案 $B$（例如放宽地域限制换取更好的学校层次），系统会顺着特征差 $\Delta\Phi_t$ 的梯度方向，增大收益维度（如学校层次）的权重均值；反之，若明确拒绝，则向反方向惩罚。  方差更新：在发生明确接受或拒绝时，系统认定获得了确定性知识，不执行启发式的方差膨胀操作 。随着明确反馈的累积，各偏好维度的不确定性在系统的探索进程中自然收敛 。  2. 模糊反馈：犹豫 (Hesitate)在真实决策中，用户常表现出“既不想放宽 A，又舍不得 B 的收益”的纠结。如果系统此时强行用梯度上升更新权重，极易引入先验偏移。因此，遇到犹豫时系统采取保守策略，主要更新方差。期望（权重）更新：保持冻结（$w_{t+1} = w_t$）。系统不执行梯度更新，防止在模糊信号下向错误方向盲目学习 。  方差更新：触发“启发式不确定性膨胀机制”（Heuristic Uncertainty Inflation） 。对该探测维度的认知方差进行惩罚性放大：
  $$v_{t+1,k} = v_{t,k} + \gamma|\Delta\phi_{t,k}|$$机制本质：犹豫意味着系统本次构造的边际替代张力不够强，没能逼出用户的真实底线。通过人为增加方差 $v$，会推高该维度在下一轮的 UCB 置信上限得分（$UCB_{t,k} = w_{t,k} + \beta\sqrt{v_{t,k}}$） 。这迫使探针规划器在下一轮继续“咬住”这个不确定维度发问，直到获得明确的 Accept 或 Reject 边界为止 。  3. 权重分布的全局合法化（投影更新）无论是经过明确反馈的梯度上升，还是经过多次交互的迭代，五维偏好（学校、专业、学费、质量、地域）的权重必须始终维持为一个合法的概率分布。因此，在每一轮 Bradley-Terry 梯度更新之后，系统必须执行额外的单纯形投影（Simplex Projection）：$$w_{t+1} = \Pi_\Delta(\tilde{w}_{t+1})$$单纯形空间定义为 $\Delta=\{w:\sum_k w_k=1, w_k \ge 0\}$ 。这一步归一化操作确保了：  即使某个维度的权重在连续拒绝中被削弱，也绝不会出现负权重。强制各维度的相对重要性总和为 1，确保后续全局效用重排时的数学尺度始终一致。


  二、 核心算法层：期望、方差与投影的 Python 实现
这是整个动态偏好追踪引擎的“心脏”。我们使用 NumPy 来实现向量化的 Bradley-Terry 梯度上升、方差膨胀以及单纯形投影。

Python
import numpy as np

class PreferenceEngine:
    def __init__(self, num_dims: int = 5, eta: float = 0.1, tau: float = 5.0, gamma: float = 0.5):
        self.eta = eta      # 学习率 \eta
        self.tau = tau      # 温度系数 \tau (控制 sigmoid 的陡峭程度)
        self.gamma = gamma  # 不确定性膨胀系数 \gamma

    def simplex_projection(self, w: np.ndarray) -> np.ndarray:
        """
        单纯形投影 (Simplex Projection)
        确保权重和为1，且所有权重 >= 0。这在工程上极其关键，防止过度拒绝导致负权重出现。
        算法复杂度 O(N log N)
        """
        u = np.sort(w)[::-1]
        cssv = np.cumsum(u)
        rho = np.nonzero(u * np.arange(1, len(w) + 1) > (cssv - 1))[0][-1]
        theta = (cssv[rho] - 1) / (rho + 1.0)
        return np.maximum(w - theta, 0)

    def update_state(self, w_t: np.ndarray, v_t: np.ndarray, delta_phi: np.ndarray, feedback: str):
        """
        根据动作执行解耦更新：
        - ACCEPT / REJECT: 更新期望 (权重)，方差不变
        - HESITATE: 更新方差，期望不变
        :param delta_phi: 探测向量差 (Phi_B - Phi_A)
        """
        w_next = np.copy(w_t)
        v_next = np.copy(v_t)

        if feedback in ["ACCEPT", "REJECT"]:
            y_t = 1.0 if feedback == "ACCEPT" else 0.0
            
            # 1. 计算选择妥协方案 B 的概率 (Bradley-Terry)
            logit = np.dot(w_t, delta_phi)
            prob_B = 1.0 / (1.0 + np.exp(-self.tau * logit))
            
            # 2. 执行逻辑斯蒂梯度上升
            gradient = self.tau * (y_t - prob_B) * delta_phi
            w_raw = w_t + self.eta * gradient
            
            # 3. 强制单纯形投影，保证权重分布合法
            w_next = self.simplex_projection(w_raw)

        elif feedback == "HESITATE":
            # 启发式不确定性膨胀：增加探测维度上的方差
            v_next = v_t + self.gamma * np.abs(delta_phi)

        return w_next, v_next


        一、 工程代码的极简闭环
因为前端直接传递了离散的确信信号，我们之前的流程编排层（LangGraph 节点）可以大幅度瘦身，彻底剥离对大模型的依赖：

Python
def preference_updater_node(state: AgentState) -> AgentState:
    # 1. 提取上下文与上轮系统生成的帕累托候选对
    option_A = state["current_probe_pair"]["A"]
    option_B = state["current_probe_pair"]["B"]
    
    # 2. 直接从前端 Payload 中获取明确的离散动作枚举值
    # 前端规约：此轮输入强制只能是 "ACCEPT", "REJECT", 或 "HESITATE"
    feedback_signal = state["messages"][-1].content.strip().upper() 
    
    # [防御性断言] 确保进入数学引擎的一定是干净的信号
    assert feedback_signal in ["ACCEPT", "REJECT", "HESITATE"], "非法反馈信号"

    # 3. 获取当前张量状态
    w_t = np.array(state["implicit_weights"])
    v_t = np.array(state["cognitive_variance"])
    delta_phi = np.array(state["current_probe_pair"]["delta_phi"])
    
    # 4. 数学引擎执行更新 (复用上轮的 PreferenceEngine)
    engine = PreferenceEngine()
    w_next, v_next = engine.update_state(w_t, v_t, delta_phi, feedback_signal)
    
    return {
        "implicit_weights": w_next.tolist(),
        "cognitive_variance": v_next.tolist(),
        "last_feedback_type": feedback_signal
    }