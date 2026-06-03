方案一：特征空间解耦（最稳妥的代码级修复）当前的错误在于，探针生成候选时用于表示“绝对否决”的物理特征值（$-9999.0$），被原封不动地塞进了需要标准正态或归一化分布的 BT 梯度下降器中。修改方案：在传入 PreferenceTracker 前，执行特征裁剪（Feature Clipping / Normalization）。我们需要区分“搜索特征空间 $\Phi_{search}$”和“学习特征空间 $\Phi_{learn}$”。在 probers.py 中，保留 features["tuition"] = -9999.0。这保证了在算帕累托前沿时，这种超预算太多的学校绝对是个劣解。在组装给 preference_tracker 的 delta_phi 时，进行单维度的幅度截断。例如，将所有维度的 $\Delta \phi_k$ 强行映射或截断到 $[-1.0, 1.0]$ 的区间内。学费超标 2200 元，在 $\Phi_{learn}$ 中不再是 -10000，而是截断为最大负向张力 -1.0。这样一来，BT 模型计算出的 $P(B)$ 可能在 $0.1 \sim 0.2$ 左右。此时用户拒绝 ($Y=0$)，梯度 $(0 - 0.1) = -0.1$，学费的隐性权重就会产生肉眼可见的上升（因为用户证明了自己很看重学费），其他无关权重自然下降。

极简代码补丁（零入侵修改）
你只需要在流入 PreferenceEngine 计算梯度之前，对传过来的 delta_phi 做一层轻量级的 Numpy 截断即可。不用改动前后的逻辑。

Python
# 在你的 preference_updater_node 或者 PreferenceEngine 的 update_state 首行
import numpy as np

def update_state(self, w_t: np.ndarray, v_t: np.ndarray, delta_phi_raw: np.ndarray, feedback: str):
    # 【新增补丁】：对传入的物理特征差进行学习域的数值截断
    # 将 -9999 / -10000 这种哨兵值截断为 -1.0，限制单维最大张量惩罚
    # 假设正常标准化后的特征差在 [-1.0, 1.0] 左右
    delta_phi_learn = np.clip(delta_phi_raw, -1.0, 1.0) 
    
    # 后续所有 BT 计算、P(B) 的推导，均使用 delta_phi_learn
    # ... [原有的 Bradley-Terry 和 单纯形投影逻辑保持不变] ...
    logit = np.dot(w_t, delta_phi_learn)
    # ... 

