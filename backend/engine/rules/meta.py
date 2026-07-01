"""
meta summarize / meta esize 命令规则
Stata:
  meta summarize
  meta esize es se, studylabel(study)
  meta forestplot / meta funnelplot
"""
META_SERIES_RULES = {
    "command": "meta",
    "python_package": "numpy+scipy",
    "subcommands": {
        "summarize": {
            "template": '''# meta summarize
print("=== Meta-Analysis Summary ===")
print(f"Number of studies: {n_studies}")
print(f"Pooled Effect: {pooled_es:.{dp}f}")
print(f"95% CI: [{ci_lower:.{dp}f}, {ci_upper:.{dp}f}]")
print(f"I-squared: {I_squared:.1f}%")
print(f"Q: {Q:.2f}, p = {p_hetero:.{dp}f}")
print(f"tau-squared: {tau2:.{dp}f}")
''',
        },
        "esize": {
            "template": "metan",  # 委托给 metan 处理
        },
        "forestplot": {
            "template": "forest",  # 委托给 forest 处理
        },
        "funnelplot": {
            "template": "funnel",  # 委托给 funnel 处理
        },
    },
    "option_map": {
        "studylabel": "study_labels",
        "esize": "effect_size_var",
        "se": "se_var",
        "random": "DL",
        "fixed": "FE",
        "common": "FE",
        "dlaird": "DL",
        "reml": "REML",
        "ml": "ML",
    },
}