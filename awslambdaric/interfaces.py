"""Protocol interfaces for AWS Lambda Runtime Interface Client."""

from typing import Protocol, Any, Dict, Tuple, Optional, List


class RuntimeClientProtocol(Protocol):
    """Protocol for Lambda runtime client operations."""
    
    marshaller: "MarshallerProtocol"
    
    def wait_next_invocation(self) -> Any: ...
    
    def post_invocation_result(self, invoke_id: Optional[str], result_data: Any, content_type: str = "application/json") -> None: ...
    
    def post_invocation_error(self, invoke_id: Optional[str], error_response_data: str, xray_fault: str) -> None: ...
    
    def post_init_error(self, error_response_data: Dict[str, Any], error_type_override: Optional[str] = None) -> None: ...


class MarshallerProtocol(Protocol):
    """Protocol for request/response marshalling."""
    
    def unmarshal_request(self, request: Any, content_type: Optional[str] = "application/json") -> Any: ...
    
    def marshal_response(self, response: Any) -> Tuple[Any, str]: ...


class LogSinkProtocol(Protocol):
    """Protocol for logging operations."""
    
    def log(self, msg: str, frame_type: Optional[bytes] = None) -> None: ...
    
    def log_error(self, message_lines: List[str]) -> None: ...