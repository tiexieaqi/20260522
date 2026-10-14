from gui_error_mapper import explain
def main():
 for c in ('model_capacity','usage_limit_exceeded','provider_timeout','script_encoding_error','source_mismatch'): assert explain(c)['technical']['error_type']==c and explain(c)['user_message']
 print('gui_error_mapper_test：全部通过')
if __name__=='__main__': main()
