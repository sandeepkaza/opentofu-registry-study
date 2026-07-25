"""fig_pipeline10.png — dual-registry mining pipeline (diagrams + graphviz).

Requires graphviz `dot` on PATH.
Run: python make_arch_diagram.py   (from the paper10 folder)
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.programming.language import Python
from diagrams.generic.storage import Storage
from diagrams.onprem.network import Internet
from diagrams.onprem.vcs import Github

graph_attr = {
    "dpi": "300",
    "fontsize": "13",
    "pad": "0.2",
    "splines": "spline",
    "nodesep": "0.35",
    "ranksep": "0.6",
}
node_attr = {"fontsize": "11"}

with Diagram(
    "",
    filename="fig_pipeline10",
    outformat="png",
    show=False,
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="LR",
):
    tf_reg = Internet("Terraform Registry API\ntop 500 x {aws, azurerm,\ngoogle} by downloads")
    tofu_reg = Internet("OpenTofu Registry API\nfull index (22,290)\n+ per-module detail")
    gh = Github("GitHub REST API\nrepo metadata")

    with Cluster("collection (dual snapshot 2026-07-18)"):
        snap = Python("snapshot.py\n1,500 TF listings\n+ tofu index + join")
        meta = Python("github_meta.py\n1,491 repos\n(1,099 reused from P4)")
        scan = Python("clone_and_scan.py\ntf-exclusive top 100/provider\ncheckov v3.3.8")

    with Cluster("raw dataset (published)"):
        d_tf = Storage("modules_tf_*.csv\nmodules_absent_*.csv")
        d_tofu = Storage("tofu_index.csv\ntofu_details_matched.csv")
        d_repo = Storage("repos_meta.csv\nrepo_tags_new.csv")
        d_scan = Storage("scan_absent.csv")

    with Cluster("analysis"):
        a13 = Python("analyze.py\nRQ1 presence\nRQ3 version currency")
        a24 = Python("rq24_analyze.py\nRQ2 governance delta\nRQ4 rule-level shape")

    p4 = Storage("Paper 4 baseline\nscan_*.csv (top 100/provider)\nre-sliced by presence")
    out = Storage("results.md\n+ figures")

    tf_reg >> snap
    tofu_reg >> snap
    snap >> d_tf
    snap >> d_tofu
    d_tf >> meta
    gh >> meta >> d_repo
    d_tf >> Edge(label="absent set") >> scan >> d_scan

    d_tf >> a13
    d_tofu >> a13
    d_repo >> a24
    d_scan >> a24
    p4 >> Edge(style="dashed", label="controls for\nscanner + date") >> a24

    a13 >> out
    a24 >> out
