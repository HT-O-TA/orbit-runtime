from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from contextlib import asynccontextmanager
from typing import Optional


class Tracer:
    _instance: Optional["Tracer"] = None

    def __init__(self, service_name: str = "orbit-runtime", endpoint: str = "localhost:4317"):
        self.service_name = service_name
        self.endpoint = endpoint
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        resource = Resource(attributes={"service.name": self.service_name})
        provider = TracerProvider(resource=resource)

        try:
            exporter = OTLPSpanExporter(endpoint=f"http://{self.endpoint}")
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
        except Exception:
            pass

        trace.set_tracer_provider(provider)
        self._initialized = True

    def get_tracer(self, name: str = "orbit-tracer") -> trace.Tracer:
        if not self._initialized:
            self.initialize()
        return trace.get_tracer(name)

    @classmethod
    def get_instance(cls) -> "Tracer":
        if cls._instance is None:
            cls._instance = Tracer()
        return cls._instance

    @asynccontextmanager
    async def start_span(self, name: str, **attributes):
        tracer = self.get_tracer()
        with tracer.start_as_current_span(name) as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)
            yield span
