def init_db() -> None:
    raise RuntimeError(
        "自动数据库 DDL 已禁用。请根据项目 Alembic 版本或审批后的 SQL，"
        "通过公司工单流程手动创建/变更数据库结构。"
    )


if __name__ == "__main__":
    init_db()
