from interface.interact import LLMInteractor

inst = LLMInteractor()
# Monkeypatch _execute to avoid network calls
inst._execute = lambda arr, model=None, temperature=None: arr + [{
    'role': 'assistant',
    'content': 'John(M): Sure, I can help.\nPriya(F): Great, thanks!'
}]

ideal = ['John(M): Hello, can you help me?\nPriya(F): Yes, I need an update.']
orig, rephrased = inst.response_transition('user input', None, ideal, [], 1)
print('ORIG:\n' + orig)
print('\nREPH:\n' + rephrased)
