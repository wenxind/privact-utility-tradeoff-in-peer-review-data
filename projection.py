import numpy as np
import cvxpy as cp
import random
import matplotlib.pyplot as plt

'''
there are 2 papers per reviewer and 2 reviews per paper  ___ k 
this number is fixed for simplicity of code
the algorithm works for different k
number of papers = number of reviewers ___ n
n can be changed
- Randomly choose assignment
- Randomly assign scores
- Add noise (for some fixed epsilon)
- Measure accuracy with and without projection
- Repeat form beginning (100 trials -- compute the mean accuracies and standard error)
'''

def create_scores(n, k):
    result = []
    for i in range(1,n*k+1):        
        result.append((i, np.random.beta(i%2+1,i%n+1)))
    #print(result)
    return result

def assign_score_papers(n, k, scoreset):
    result = dict()
    for i in range(n):
        result[scoreset[i*k]] = i+1
        result[scoreset[i*k+1]]= i+1
    return result


def valid_assignments(n, k, scoreset):
    result = []
    for i in range(n):
        for j in range(k):
            for restscore in (scoreset[i*k+k:]):
                result.append((scoreset[i*k+j], restscore))
    return result

def no_cross(a, b):
    if a[0]==b[0] or a[0]==b[1] or a[1]==b[0] or a[1]==b[1]:
        return False
    else:
        return True

def edge_map(assignments):
    graph = dict()
    for (s1, s2) in assignments:
        graph[(s1, s2)] = set()

    for i in range(len(assignments)):
        for (s1, s2) in assignments[i+1:]:
            if no_cross(assignments[i], (s1, s2)):
                graph[assignments[i]].add((s1, s2))
                graph[(s1, s2)].add(assignments[i])

    return graph

def sort_assignments(assignments):
    result = sorted(assignments, key=lambda x: x[0][1]+x[1][1])
    return result

def lr_chain(sorted_assignments, graph):
    chain_map = dict()
    sort_map = dict()
    total_assignments = len(sorted_assignments)

    for i in range(total_assignments):
        chain_map[sorted_assignments[i]] = [1, 1]
        sort_map[sorted_assignments[i]] = i

    for i in range(total_assignments):
        elem = sorted_assignments[i]
        neighbors = graph[elem]
        left = []
        for (a, b) in neighbors:   
            if sort_map[(a, b)] < sort_map[elem]:
                left.append(chain_map[(a, b)][0]+1)
        if left != []:
            chain_map[elem][0] = max(left)

    for i in range(total_assignments):
        elem = sorted_assignments[total_assignments-1-i]
        neighbors = graph[elem]
        right = []
        for (a, b) in neighbors:   
            if sort_map[(a, b)] > sort_map[elem]:
                right.append(chain_map[(a, b)][1]+1)
        if right != []:
            chain_map[elem][1] = max(right)

    return chain_map

def paper_use(n):
    result = dict()
    for i in range(1, n+1):
        result[i] = [False, False]
    return result


def check_rest_scores(n, should_have, paper_already_use):
    for i in range(1, n+1):
        if paper_already_use[i].count(False) > should_have:
            return False
    return True


def sum_over(bound_assign):
    result = []
    for (s1, s2) in bound_assign:
        result.append((s1[1]+s2[1])/2)
    #print(result)
    return result

def check_assignment(n, k, l):
    for i in range(n):
        if l[2*i] == l[2*i+1]:
            return False
    return True


#already assume k = 2 in multiple places below
def actual_score(n, k, scoreset):
    l = list(range(1, n+1)) + list(range(1, n+1))
    #score_to_paper = assign_score_papers(n, k, scoreset)

    random.shuffle(l)
    while(True):
        random.shuffle(l)
        if check_assignment(n, k, l) == True:
            break
    for i in range(len(scoreset)):
        paper = (scoreset[i][0]+1)//2
        j = l.index(paper)
        l[j] = scoreset[i]
    result = []
    for i in range(n):
        result.append((l[2*i], l[2*i+1]))
   
    real_data = sorted(sum_over(result))
    return real_data


def create_bounds(n, k, scoreset):
   
    lower_paper_use = paper_use(n)
    upper_paper_use = paper_use(n)
    
    assignments = valid_assignments(n, k, scoreset)
    sorted_assignments = sort_assignments(assignments)
    graph = edge_map(assignments)
    chain_map = lr_chain(sorted_assignments, graph)

    total_assignments = len(sorted_assignments)

    lower_bound_assign = []
    i = 0
    rank = 0
    while rank < n:
        while i < total_assignments:
            (s1, s2) = sorted_assignments[i]
            paper1 = (s1[0]+1)//2
            paper2 = (s2[0]+1)//2
            lower_paper_use[paper1][(s1[0]+1)%2] = True
            lower_paper_use[paper2][(s2[0]+1)%2] = True
            left_chain = chain_map[(s1, s2)][0]
            if rank > n-3:
                should_have = n-rank-1
                bool1 = check_rest_scores(n, should_have, lower_paper_use)
            else:
                bool1 = True
            if bool1 and left_chain>rank:
                lower_bound_assign.append((s1, s2))
                rank+=1
                i+=1
                break
            else:
                i += 1

    upper_bound_assign = []
    i = 0
    rank = 0
    while rank < n:
        while i < total_assignments:
            (s1, s2) = sorted_assignments[total_assignments-1-i]
            paper1 = (s1[0]+1)//2
            paper2 = (s2[0]+1)//2
            upper_paper_use[paper1][(s1[0]+1)%2] = True
            upper_paper_use[paper2][(s2[0]+1)%2] = True
            right_chain = chain_map[(s1, s2)][1]
            if rank > n-3:
                should_have = n-rank-1
                bool1 = check_rest_scores(n, should_have, upper_paper_use)
            else:
                bool1 = True
            if bool1 and right_chain>rank:
                upper_bound_assign = [(s1, s2)] + upper_bound_assign 
                rank+=1
                i+=1
                break
            else:
                i += 1
    return(sum_over(lower_bound_assign), sum_over(upper_bound_assign))



#noise mean mu, variance 2b^2

def projection(n, k):
    scoreset = create_scores(n, k)

    total_score = sum(score for (lable, score) in scoreset)/k
   
    real_data = actual_score(n, k, scoreset)

    real_data_array = np.array(real_data)
   
    noisy_data_array = real_data_array + np.random.laplace(0, 1, n)
   
    
    no_projection_error = np.sum(np.square(noisy_data_array-real_data_array))

    (lower_bound, upper_bound) = create_bounds(n, k, scoreset)
    
    project_data = cp.Variable(n)
    constraints = [project_data <= np.array(upper_bound), project_data >= np.array(lower_bound)]
    
    constraints.append(sum(project_data) == total_score)
    for i in range(n-1):
        constraints.append(project_data[i]<= project_data[i+1])

    prob1 = cp.Problem(cp.Minimize(cp.sum_squares(project_data - noisy_data_array)), constraints)
    prob1.solve()
   
    projection_error = np.sum(np.square(project_data.value - real_data_array))
    
    project_data_bl = cp.Variable(n)
    constraints_bl = [sum(project_data_bl) == total_score]
    for i in range(n):
        constraints_bl+=[project_data_bl[i] <= 1, project_data_bl[i] >= 0]
    for i in range(n-1):
        constraints_bl.append(project_data_bl[i]<= project_data_bl[i+1])
    prob2 = cp.Problem(cp.Minimize(cp.sum_squares(project_data_bl - noisy_data_array)), constraints_bl)
    prob2.solve()
    projection_error_bl = np.sum(np.square(project_data_bl.value - real_data_array))

    return(no_projection_error, projection_error, projection_error_bl)



def simulation(n, k, times):
    
    noisy_error = []
    projected_error = []
    projected_error_bl = []
    for i in range(times):
        (e1, e2, e3) = projection(n, k)
        noisy_error.append(e1)
        projected_error.append(e2)
        projected_error_bl.append(e3)

    noisy_result = np.mean(noisy_error)
    projection_result = np.mean(projected_error)
    projection_result_bl = np.mean(projected_error_bl)
    f = open("bata_1.txt", "a")
    f.write("There are %d reviewers\n" %n)
    f.write("Noisy **********************************\n")
    f.write(str(noisy_error)+'\n')
    f.write("Our ************************************\n")
    f.write(str(projected_error)+'\n')
    f.write("Baseline *******************************\n")
    f.write(str(projected_error_bl)+'\n')
    f.write('\n')
    f.close()
    
    print("There are", n, "reviewrs *****************************")
    print(noisy_error, projected_error, projected_error_bl)
    print()
    return(noisy_result, projection_result, projection_result_bl, np.std(noisy_error), np.std(projected_error), np.std(projected_error_bl))



def plot():
    #x-axis
    reviewers=[]
    
    #y-axis1 ==> noisy data
    noisy_accuracy = []
    #y-error1 ==> noisy data std error of mean
    noisy_sem = []

    #y-axis2 ==> projected data
    projection_accuracy = []
    #y-error2 ==> projection data std error of mean
    projection_sem = []

    #y-axis3 ==> baseline projected data
    projection_accuracy_bl = []
    #y-error3 ==> baseline projection data std error of mean
    projection_sem_bl = []

    for numreviewer in range(10, 51, 10):
        reviewers.append(numreviewer)
        times = 100
        tsqrt = np.sqrt(times)
        (nr, pr, prbl, nstd, pstd, prblstd) = simulation(numreviewer, 2, times)
        noisy_accuracy.append(nr)
        noisy_sem.append(nstd/tsqrt)

        projection_accuracy.append(pr)
        projection_sem.append(pstd/tsqrt)

        projection_accuracy_bl.append(prbl)
        projection_sem_bl.append(prblstd/tsqrt)

        

    plt.figure(figsize=(10,7))
    noisy, = plt.plot(a_list, noisy_accuracy, 's',label = "Noisy", color='r', markersize=18)
    plt.errorbar(a_list, noisy_accuracy, yerr = noisy_sem, color='r', capsize=6, elinewidth=8, linestyle='--', linewidth=4)

    projectedbl, = plt.plot(a_list, projection_accuracy_bl, '^',label = "Baseline projection", color='g', markersize=18)
    plt.errorbar(a_list, projection_accuracy_bl, yerr = projection_sem_bl, color='g', capsize=8, elinewidth=6, linestyle='-.', linewidth=4)

    projected, = plt.plot(a_list, projection_accuracy, 'o',label = "Our algorithm", color='b', markersize=18)
    plt.errorbar(a_list, projection_accuracy, yerr = projection_sem, color='b', capsize=6, elinewidth=8, linestyle='-', linewidth=4)
    #projected.set_label('After projection')

    plt.yscale('log')
    plt.ylabel('Mean squared error')
    plt.xlabel('Value of a')
    plt.grid(True)

    plt.savefig('beta(a,a).pdf', bbox_inches='tight')
    plt.show()
    return(noisy_accuracy, noisy_sem, projection_accuracy, projection_sem, projection_accuracy_bl, projection_sem_bl)






