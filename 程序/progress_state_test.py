from progress_state import calculate_progress
def main():
 assert calculate_progress({i:'completed' for i in range(1,7)})['percent']==50
 assert calculate_progress({i:'completed' for i in range(1,7)},range(1,7))['scope_complete']
 assert calculate_progress({1:'completed',2:'failed'})['completed']==1
 print('progress_state_test：全部通过')
if __name__=='__main__': main()
