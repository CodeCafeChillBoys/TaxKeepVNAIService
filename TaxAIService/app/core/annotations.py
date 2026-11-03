from typing import TypeVar, Any, Callable, Union

T = TypeVar("T")


def exclude_from_coverage(
    target: Union[T, None] = None,
    reason: str = ""
) -> Union[T, Callable[[T], T]]:
    """
    Annotation / Decorator đánh dấu Class hoặc Function không cần đo Code Coverage
    (Tương đương với [ExcludeFromCodeCoverage] trong C# .NET).

    Cách sử dụng:
        1. Không cần tham số:
            @exclude_from_coverage
            class MyDto:
                pass

        2. Kèm lý do:
            @exclude_from_coverage(reason="Chỉ là tầng DTO không chứa nghiệp vụ phức tạp")
            class AnotherDto:
                pass
    """
    if target is None or isinstance(target, str):
        # Được gọi có ngoặc: @exclude_from_coverage(...) hoặc @exclude_from_coverage(reason="...")
        def decorator(real_target: T) -> T:
            return real_target
        return decorator

    # Được gọi trực tiếp không ngoặc: @exclude_from_coverage
    return target
