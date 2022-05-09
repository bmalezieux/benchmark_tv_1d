from benchopt import BaseSolver
from benchopt.stopping_criterion import SufficientProgressCriterion
from benchopt import safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np
    from scipy.sparse import spdiags
    from scipy import optimize


class Solver(BaseSolver):
    """Dual Projected gradient descent for synthesis formulation."""
    name = 'ChamPoke'

    stopping_criterion = SufficientProgressCriterion(
        patience=20, strategy='callback'
    )

    # any parameter defined here is accessible as a class attribute
    parameters = {'sigma': [0.5],
                  'theta': [1.]}

    def set_objective(self, A, reg, y, c, delta, data_fit):
        self.reg = reg
        self.A, self.y = A, y
        self.c = c
        self.delta = delta
        self.data_fit = data_fit

    def run(self, callback):
        len_y = len(self.y)
        data = np.array([np.ones(len_y), -np.ones(len_y)])
        diags = np.array([0, 1])
        D = spdiags(data, diags, len_y-1, len_y)
        tau = 1. / (np.linalg.norm(self.A, ord=2)**2)
        I_tauAtA_inv = np.linalg.pinv(np.identity(
            len_y) + tau * self.A.T @ self.A)
        tauAty = tau * self.A.T @ self.y
        v = np.zeros(len_y - 1)
        u = self.c * np.ones(len_y)
        u_bar = u

        while callback(u):
            u_old = u
            v = np.clip(v + self.sigma * D @ u_bar, -self.reg, self.reg)
            u_tmp = u - tau * D.T @ v

            if self.data_fit == 'quad':
                u = I_tauAtA_inv @ (tauAty + u_tmp)
            else:
                u_new = I_tauAtA_inv @ (tauAty + u_tmp)
                R = self.y - self.A @ u_new

                def f(u):
                    return abs(u - u_tmp - tau * self.delta * self.A.T @
                               np.sign(self.y - self.A @ u)).sum()

                u = np.where(np.abs(R) < self.delta,
                             u_new,
                             optimize.minimize(f, u).x)

            u_bar = u + self.theta * (u - u_old)
        self.u = u

    def get_result(self):
        return self.u
