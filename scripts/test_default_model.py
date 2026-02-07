from interface.interact import LLMInteractor

class DummyClient:
    class chat:
        class completions:
            @staticmethod
            def create(model, messages, temperature, top_p, n, stream, presence_penalty, frequency_penalty):
                print('MODEL_USED:', model)
                return type('R', (), {'choices':[type('C', (), {'message':type('M', (), {'content':'ok'})()})()]})()

inst = LLMInteractor()
# Replace real client with dummy to capture model
inst.client = DummyClient()
# Call _execute without passing model so default is used
inst._execute([{'role':'user','content':'test'}])
