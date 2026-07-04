from fastapi import HTTPException, status


def reject_physical_delete(label: str = "资源") -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail=f"公司 MySQL 规范禁止物理删除{label}；请使用停用、归档、状态流转或版本替换",
    )
