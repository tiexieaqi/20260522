"""离线验证官方模型容量回退策略；不调用 Codex、不调用网络。"""
class FakeProvider:
    def __init__(self, errors): self.errors=list(errors); self.calls=[]
    def call(self, model):
        self.calls.append(model)
        if self.errors: raise RuntimeError(self.errors.pop(0))
        return 'OK'

def choose(provider):
    preferred='gpt-5.6-luna'; selected=preferred; fallback=False
    try: provider.call(preferred)
    except RuntimeError as e:
        if 'capacity' not in str(e): raise
        selected='gpt-5.6-terra'; fallback=True; provider.call(selected)
    return selected,fallback

def main():
    p=FakeProvider(['model_capacity']); s,f=choose(p); assert s=='gpt-5.6-terra' and f and p.calls==['gpt-5.6-luna','gpt-5.6-terra']
    for error in ('usage_limit_exceeded','auth_error','schema_error'):
        try: choose(FakeProvider([error])); raise AssertionError(error)
        except RuntimeError as e: assert str(e)==error
    print('codex_capacity_fallback_test：全部通过')
if __name__=='__main__': main()
