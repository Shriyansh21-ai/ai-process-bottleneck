import time

class BaseAgent:
    name = "base-agent"

    def __init__(self, trace):
        self.trace = trace

    async def execute(self, func, input_data):
        start = time.time()
        try:
            output = await func()
            self.trace.record(
                agent=self.name,
                input_data=input_data,
                output_data=output,
                start_time=start
            )
            return output
        except Exception as e:
            self.trace.record(
                agent=self.name,
                input_data=input_data,
                output_data=None,
                start_time=start,
                status="error",
                error=str(e)
            )
            raise
