from computecommons.enums import IsolationKind
from computecommons.virtualisation import ExecutionContext, ExecutionLayer


def test_nested_execution_context() -> None:
    context = ExecutionContext(
        layers=(
            ExecutionLayer(IsolationKind.VIRTUAL_MACHINE, "vmware"),
            ExecutionLayer(IsolationKind.APPLICATION_CONTAINER, "containerd"),
            ExecutionLayer(IsolationKind.LANGUAGE_RUNTIME, "cpython"),
        )
    )
    assert context.is_virtualized
    assert context.innermost.technology == "cpython"
