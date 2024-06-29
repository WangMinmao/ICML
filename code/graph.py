import json
import networkx as nx
import matplotlib.pyplot as plt

# 读取并解析文件
with open('提交版本/predictions.json', 'r') as file:
    predictions = [json.loads(line) for line in file]

with open('ICML/starting_kit/axioms.json', 'r') as file:
    axioms = [json.loads(line) for line in file]

# 提取axioms中存在的节点
axioms_nodes = {ax["theorem"] for ax in axioms}

# 构建有向图
G = nx.DiGraph()

# 添加节点和边
for theorem in predictions:
    theorem_name = theorem["theorem"]
    references = theorem.get("references", [])
    G.add_node(theorem_name)
    for ref in references:
        G.add_node(ref)
        G.add_edge(ref, theorem_name)  # 从引用到定理添加边

# 计算仅存在于axioms中的节点的中心性
centrality = nx.degree_centrality(G)
axioms_centrality = {node: centrality[node] for node in axioms_nodes if node in centrality}

# 按度中心性降序排序
sorted_axioms_centrality = sorted(axioms_centrality.items(), key=lambda item: item[1], reverse=True)

# 打印排序后的节点中心性
print("Sorted Axioms by Centrality:")
nodes=[]
for node, centrality_value in sorted_axioms_centrality:
    print(f"Node: {node}, Centrality: {centrality_value}")
    nodes.append(node)
    
print(nodes)

print(f'Total number of axioms: {len(sorted_axioms_centrality)}')

# 可视化图结构（可选）
plt.figure(figsize=(12, 12))
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_size=700, node_color="skyblue", font_size=10, font_weight="bold", arrowsize=20)
plt.show()
