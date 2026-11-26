Optimization Stability

We optimize the objective in Equation (2) with Adam and a fixed step size of 0.001. The training procedure does not converge when the gradient norm exceeds 10, so we clip the gradient at that value. The update rule is $x_{t+1} = x_t - \eta \nabla f(x_t)$, where $\eta$ is the step size.
