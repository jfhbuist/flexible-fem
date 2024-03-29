#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 16:50:37 2021

@author: jfhbuist
"""

import numpy as np
import scipy as sp


class Grid:
    def __init__(self, dim, L, nx, H=None, ny=None):
        self.dim = dim
        if self.dim == 1:
            n = nx
            self.xy_vert, self.xy_elem, self.xy_bound, self.elmat, self.belmat, self.loc_bound = self.generate_mesh_1D(L, n)
        elif self.dim == 2:
            self.xy_vert, self.xy_elem, self.xy_bound, self.elmat, self.belmat, self.loc_bound = self.generate_mesh_2D(L, H, nx, ny)

    def generate_mesh_1D(self, L, n):
        xy_vert = np.linspace(0, L, n)
        xy_elem = (xy_vert[0:n-1]+xy_vert[1:n])/2
        # dx = 1/(n-1)
        xy_bound = np.array([0, L])  # boundary element coordinates

        # This matrix lists the vertices of each element.
        # ie for element i, evaluate elmat[i], to list the two vertices which
        # border element i
        elmat = np.zeros((n-1, 2)).astype(int)
        for idx, element in enumerate(elmat):
            elmat[idx, 0] = idx
            elmat[idx, 1] = idx + 1

        # This matrix list the vertices of each boundary element.
        # ie for boundary element i, evaluate belmat(i), to list the vertex to which it is connected
        belmat = np.zeros((len(xy_bound), 1)).astype(int)
        loc_bound = []  # boundary element locations
        belmat[0] = 0  # first boundary element is connected to vertex 0
        loc_bound.append("left")
        belmat[1] = n-1  # last boundary element is connected to vertex n-1
        loc_bound.append("right")
        return xy_vert, xy_elem, xy_bound, elmat, belmat, loc_bound

    def generate_mesh_2D(self, L, H, nx, ny):
        # Create vertices with coordinates
        x = np.linspace(0, L, nx)
        y = np.linspace(0, H, ny)
        xm, ym = np.meshgrid(x, y)
        xy_vert = np.zeros((nx*ny, 2))
        idx = 0
        for i in range(nx):
            for j in range(ny):
                xy_vert[idx] = np.array([xm[j, i], ym[j, i]])
                idx += 1

        # Make triangle elements, based on squares
        xy_elem = np.zeros((2*(nx-1)*(ny-1), 2))
        elmat = np.zeros((len(xy_elem), 3)).astype(int)
        t_idx = 0
        for i in range(nx-1):
            for j in range(ny-1):
                elmat[t_idx, 0] = i*ny+j  # lower left
                elmat[t_idx, 1] = i*ny+ny+j+1  # upper right
                elmat[t_idx, 2] = i*ny+j+1  # upper left
                xy_elem[t_idx] = (xy_vert[elmat[t_idx, 0]] + xy_vert[elmat[t_idx, 1]] + xy_vert[elmat[t_idx, 2]])/3
                t_idx += 1
                elmat[t_idx, 0] = i*ny+j  # lower left
                elmat[t_idx, 1] = i*ny+ny+j  # lower right
                elmat[t_idx, 2] = i*ny+ny+j+1  # upper right
                xy_elem[t_idx] = (xy_vert[elmat[t_idx, 0]] + xy_vert[elmat[t_idx, 1]] + xy_vert[elmat[t_idx, 2]])/3
                t_idx += 1
        # plt.scatter(xy_elem[:,0],xy_elem[:,1])

        # Create boundary elements with coordinates for their centers
        xy_bound = np.zeros((2*(nx-1)+2*(ny-1), 2))
        belmat = np.zeros((len(xy_bound), 2)).astype(int)
        loc_bound = []  # boundary element locations
        b_idx = 0
        for j in range(ny-1):  # left
            belmat[b_idx, 0] = 0 + j
            belmat[b_idx, 1] = 0 + j + 1
            xy_bound[b_idx] = (xy_vert[belmat[b_idx, 0]] + xy_vert[belmat[b_idx, 1]])/2
            loc_bound.append("left")
            b_idx += 1
        for j in range(ny-1):  # right
            belmat[b_idx, 0] = (nx-1)*ny + j
            belmat[b_idx, 1] = (nx-1)*ny + j + 1
            xy_bound[b_idx] = (xy_vert[belmat[b_idx, 0]] + xy_vert[belmat[b_idx, 1]])/2
            loc_bound.append("right")
            b_idx += 1
        for i in range(nx-1):  # bottom
            belmat[b_idx, 0] = 0 + i*ny
            belmat[b_idx, 1] = 0 + i*ny + ny
            xy_bound[b_idx] = (xy_vert[belmat[b_idx, 0]] + xy_vert[belmat[b_idx, 1]])/2
            loc_bound.append("bottom")
            b_idx += 1
        for i in range(nx-1):  # top
            belmat[b_idx, 0] = ny-1 + i*ny
            belmat[b_idx, 1] = ny-1 + i*ny + ny
            xy_bound[b_idx] = (xy_vert[belmat[b_idx, 0]] + xy_vert[belmat[b_idx, 1]])/2
            loc_bound.append("top")
            b_idx += 1
        # plt.scatter(xy_bound[:,0],xy_bound[:,1])

        return xy_vert, xy_elem, xy_bound, elmat, belmat, loc_bound


class Discretization:
    def __init__(self, dim):
        """Define discretization by setting basis and test functions."""
        self.dim = dim
        # Isoparametric mapping: Use same shape functions for basis functions as for coordinate
        # transformation
        self.basis_functions, self.dphidxieta = self.define_shape_functions()
        self.basis_functions_bound, self.dphidxieta_bound = self.define_shape_functions(True)
        # Standard Galerkin: Use same shape functions for test functions as for basis functions
        self.test_functions, self.dvdxieta = self.define_shape_functions()
        self.test_functions_bound, self.dvdxieta_bound = self.define_shape_functions(True)

    def define_shape_functions(self, boundary=False):
        if boundary:
            dim = self.dim - 1
        else:
            dim = self.dim
        if dim == 0:
            shape_functions = self.define_shape_functions_point()
        elif dim == 1:
            shape_functions = self.define_shape_functions_line()
        elif dim == 2:
            shape_functions = self.define_shape_functions_triangle()
        return shape_functions

    def define_shape_functions_point(self):
        """Define shape functions for a zero-width element defined by one vertex."""
        # x0 is the only bounding vertex, and is also the midpoint of the element
        # N0 is 1 at x0, and zero elsewhere
        # define as python function
        n0 = lambda xieta: 1
        shape_functions = [n0]
        dndxieta = np.array([[0]])
        return shape_functions, dndxieta

    def define_shape_functions_line(self):
        """Define shape functions for an element defined by its two bounding vertices."""
        # The reference element is a line with vertices xi = (0), (1)
        # for a given element, n0 is 1 at the left vertex, and corresponds to elmat[i,0]
        # for a given element, n1 is 1 at the right vertex, and corresponds to elmat[i,1]
        # xieta is a list of length 1, with xieta[0] = xi
        # define as python function
        n0 = lambda xieta: 1-xieta[0]
        n1 = lambda xieta: xieta[0]
        shape_functions = [n0, n1]
        dndxieta = np.array([[-1], [1]])
        return shape_functions, dndxieta

    def define_shape_functions_triangle(self):
        """Define shape functions for an element defined by its three bounding vertices."""
        # These can be oriented arbitrarily, but the reference element is a right-angled triangle
        # with vertices xi, eta = (0,0), (1,0), (0,1).
        # for a given element, n0 is 1 at the bottom left vertex, and corresponds to elmat[i,0]
        # for a given element, n1 is 1 at the bottom right vertex, and corresponds to elmat[i,1]
        # for a given element, n2 is 1 at top left vertex, and corresponds to elmat[i,2]
        # xieta is a list of length 2, with xieta[0] = xi and xieta[1] = eta
        # define as python function
        n0 = lambda xieta: 1-xieta[0]-xieta[1]
        n1 = lambda xieta: xieta[0]
        n2 = lambda xieta: xieta[1]
        shape_functions = [n0, n1, n2]
        dndxieta = np.array([[-1, -1], [1, 0], [0, 1]])
        return shape_functions, dndxieta

    def get_jacobian(self, vert_coords, boundary=False):
        """Calculate jacobian dxy/dxieta."""
        if boundary:
            dim = self.dim - 1
        else:
            dim = self.dim
        if dim == 0:
            jacobian = 0
        elif dim == 1:
            jacobian = self.get_jacobian_line(vert_coords)
        elif dim == 2:
            jacobian = self.get_jacobian_triangle(vert_coords)
        return jacobian

    def get_jacobian_line(self, vert_coords):
        """For line element, calculate jacobian dx/dxi."""
        # Use coordinate transformation xi = (x - x0)/dx, dxi/dx = 1/dx, dx = dx dxi
        # This implies x = xi*dx + x0
        # So Jacobian = dx
        jacobian = np.array([np.matmul(np.transpose(vert_coords), self.dphidxieta)])
        return jacobian

    def get_jacobian_triangle(self, vert_coords):
        """For triangle element, calculate jacobian dxy/dxieta."""
        # This is the 2x2 matrix [[dx/dxi, dy/dxi],[dx/deta, dy/deta]]
        # It can be calculated by multiplying the matrices dphi/dxieta and vert_coords
        jacobian = np.matmul(np.transpose(vert_coords), self.dphidxieta)
        # jacobian = np.matmul(vert_coords, self.dphidxieta)
        return jacobian

    def coordinate_transformation(self, vert_coords, function_xy):
        """Transform function of xy to function of xieta."""
        dim = self.dim
        if dim == 1:
            function_xieta = self.coordinate_transformation_line(vert_coords, function_xy)
        elif dim == 2:
            function_xieta = self.coordinate_transformation_triangle(vert_coords, function_xy)
        return function_xieta

    def coordinate_transformation_line(self, vert_coords, function_xy):
        """Transform 1D function of x to function of xi."""
        # Use coordinate transformation xi = (x - x0)/dx, dxi/dx = 1/dx, dx = dx dxi
        # This implies x = xi*dx + x0
        # This can be written systematically as x = x0*phi0(xi) + x1*phi1(xi)
        phi = self.basis_functions
        x0 = vert_coords[0]
        x1 = vert_coords[1]
        function_xieta = lambda xieta: function_xy([x0*phi[0](xieta)+x1*phi[1](xieta)])
        return function_xieta

    def coordinate_transformation_triangle(self, vert_coords, function_xy):
        """Transform 2D function of xy to function of xieta."""
        # Use x = x0*phi0(xi, eta) + x1*phi1(xi, eta) + x2*phi2(xi, eta)
        # and y = y0*phi0(xi, eta) + y1*phi1(xi, eta) + y2*phi2(xi, eta)
        phi = self.basis_functions
        x0 = vert_coords[0, 0]
        y0 = vert_coords[0, 1]
        x1 = vert_coords[1, 0]
        y1 = vert_coords[1, 1]
        x2 = vert_coords[2, 0]
        y2 = vert_coords[2, 1]
        function_xieta = lambda xieta: function_xy([
                                        x0*phi[0](xieta)+x1*phi[1](xieta)+x2*phi[2](xieta),
                                        y0*phi[0](xieta)+y1*phi[1](xieta)+y2*phi[2](xieta)
                                        ])
        return function_xieta

    def coordinate_transformation_bound(self, vert_coords, function_xy):
        """Transform function of xy to function of xieta, on boundary element."""
        dim = self.dim
        if dim == 1:
            function_tau, det = self.coordinate_transformation_1D_bound(vert_coords, function_xy)
        elif dim == 2:
            function_tau, det = self.coordinate_transformation_2D_bound(vert_coords, function_xy)
        return function_tau, det

    def coordinate_transformation_1D_bound(self, vert_coords, function_xy):
        """For a boundary element in a 1D domain, transform 1D function of x to a 0D function of
        nothing."""
        # No real coordinate transformation necessary, just evaluate function at boundary point
        x0 = vert_coords[0]
        function_tau = lambda tau: function_xy([x0])
        det = 1
        return function_tau, det

    def coordinate_transformation_2D_bound(self, vert_coords, function_xy):
        """For a boundary element in a 2D domain, transform 2D function of xy to a 1D function of
        tau."""
        # Use boundary shape functions (for line element)
        # Use x = x0+tau*(x1-x0) = x0*phi[0](tau)+x1*phi[1](tau)
        # and y = y0+tau*(y1-y0) = y0*phi[0](tau)+y1*phi[1](tau)
        phi = self.basis_functions_bound
        x0 = vert_coords[0, 0]
        y0 = vert_coords[0, 1]
        x1 = vert_coords[1, 0]
        y1 = vert_coords[1, 1]
        function_tau = lambda tau: function_xy([x0*phi[0](tau)+x1*phi[1](tau),
                                                y0*phi[0](tau)+y1*phi[1](tau)])
        # To integrate over tau we need to multiply by the following
        det = np.sqrt((x1-x0)**2 + (y1-y0)**2)
        return function_tau, det

    def coordinate_transformation_inverse(self, vert_coords, function_xieta):
        """Transform function of xieta to function of xy."""
        if self.dim == 1:
            function_xy = self.coordinate_transformation_inverse_line(vert_coords, function_xieta)
        elif self.dim == 2:
            function_xy = self.coordinate_transformation_inverse_triangle(vert_coords, function_xieta)
        return function_xy

    def coordinate_transformation_inverse_line(self, vert_coords, function_xieta):
        """Transform 1D function of xi to function of x."""
        # Use coordinate transformation xi = (x - x0)/dx, dxi/dx = 1/dx, dx = dx dxi
        x0 = vert_coords[0]
        x1 = vert_coords[1]
        dx_i = abs(x1 - x0)
        function_xy = lambda xy: function_xieta([(xy[0] - x0)/dx_i])
        return function_xy

    def coordinate_transformation_inverse_triangle(self, vert_coords, function_xieta):
        """Transform 2D function of xieta to function of xy."""
        # Use (x, y) = (x0, y0) + (dxy/dxieta)*(xi, eta)
        x0 = vert_coords[0, 0]
        y0 = vert_coords[0, 1]
        x1 = vert_coords[1, 0]
        y1 = vert_coords[1, 1]
        x2 = vert_coords[2, 0]
        y2 = vert_coords[2, 1]
        dxydxieta = np.array([[-x0+x1, -x0+x2], [-y0+y1, -y0+y2]])
        # (xi, eta) = (dxieta/dxy)*(x-x0, y-y0)
        dxietadxy = np.linalg.inv(dxydxieta)
        function_xy = lambda xy: function_xieta([
                                    dxietadxy[0, 0]*(xy[0] - x0) + dxietadxy[0, 1]*(xy[1] - y0),
                                    dxietadxy[1, 0]*(xy[0] - x0) + dxietadxy[1, 1]*(xy[1] - y0)
                                    ])
        return function_xy

    def integrate_element(self, integrand, boundary=False):
        """Integrate function of xieta over element."""
        if boundary:
            dim = self.dim - 1
        else:
            dim = self.dim
        if dim == 0:
            result = self.integrate_element_point(integrand)
        elif dim == 1:
            result = self.integrate_element_line(integrand)
        elif dim == 2:
            result = self.integrate_element_triangle(integrand)
        return result

    def integrate_element_point(self, integrand):
        """Integrate 0D function of xi over 0D element."""
        # We need to integrate over the boundary.
        # We assume the boundary conditions are for the component normal to the boundary.
        # So we do not have to add minus signs to some boundaries.
        # The length of the boundary element is zero, so the integral is equal to the integrand,
        # evaluated at the vertex
        result = integrand([0])
        return result

    def integrate_element_line(self, integrand):
        """Integrate 1D function of xi over element."""
        integrand_expanded = lambda xi: integrand([xi])
        result = sp.integrate.quad(integrand_expanded, 0, 1)[0]
        return result

    def integrate_element_triangle(self, integrand):
        """Integrate 2D function of xieta over element."""
        integrand_expanded = lambda eta, xi: integrand([xi, eta])
        eta_lower_bound = 0
        eta_upper_bound = lambda xi: 1 - xi
        result = sp.integrate.dblquad(integrand_expanded, 0, 1, eta_lower_bound, eta_upper_bound)[0]
        return result

    def check_if_point_in_element(self, vert_coords, point_coords):
        """Check if point with given coordinates is in the element defined by vert_coords."""
        if self.dim == 1:
            check = self.check_if_point_in_element_line(vert_coords, point_coords)
        elif self.dim == 2:
            check = self.check_if_point_in_element_triangle(vert_coords, point_coords)
        return check

    def check_if_point_in_element_line(self, vert_coords, point_coords):
        """Check if point with given coordinates is in the 1D element defined by vert_coords."""
        xi_xieta = lambda xieta: xieta[0]
        xi_xy = self.coordinate_transformation_inverse_line(vert_coords, xi_xieta)
        xp = point_coords
        xip = xi_xy(xp)
        if (xip >= 0) and (xip <= 1):
            check = True
        else:
            check = False
        return check

    def check_if_point_in_element_triangle(self, vert_coords, point_coords):
        """Check if point with given coordinates is in the 2D element defined by vert_coords."""
        xi_xieta = lambda xieta: xieta[0]
        eta_xieta = lambda xieta: xieta[1]
        xi_xy = self.coordinate_transformation_inverse_triangle(vert_coords, xi_xieta)
        eta_xy = self.coordinate_transformation_inverse_triangle(vert_coords, eta_xieta)
        xyp = point_coords
        xip = xi_xy(xyp)
        etap = eta_xy(xyp)
        if (((xip >= 0) and (etap >= 0)) and (xip + etap <= 1)):
            check = True
        else:
            check = False
        return check


class SourceOperator:
    """Discrete operator determined by a set function."""
    def __init__(self, grid, discretization, operators):
        self.grid = grid
        self.discretization = discretization
        self.d = self.combine_operators(operators)

    def combine_operators(self, operators):
        d = np.zeros(len(self.grid.xy_vert))
        for idx, operator in enumerate(operators):
            d = d + operator.d
        return d

    def assemble_source_vector(self):
        """Operates on vertices.

        For each vertex, sum the contributions of all its neighbouring elements.
        """
        grid = self.grid
        d = np.zeros(len(grid.xy_vert))
        for i, xy_i in enumerate(grid.xy_elem):  # loop over elements
            # xy_i is center of current element
            elem_vertices = grid.elmat[i]
            d_elem = self.generate_element_vector(elem_vertices)
            for j in range(len(elem_vertices)):  # loop over equations for vertex coefficients
                # Each equation is associated with one test function.
                # We are now considering the contribution of one element to two different equations (in 1D).
                # Each equation is associated with two elements (in 1D).
                # So the equation will be revisted when considering a different element.
                # From vertex i we have contributions (in 1D):
                # \int_{x_{i-1}}^{x_{i}} phi1*f + \int_{x_{i}}^{x_{i+1}} phi0*f
                d[grid.elmat[i, j]] += d_elem[j]
                # index: equation/test function
        return d

    def generate_element_vector(self, elem_vertices):
        """Operates on elements."""
        grid = self.grid
        discretization = self.discretization
        vert_coords = np.array([grid.xy_vert[ev] for ev in elem_vertices])
        # get test functions
        test_functions = discretization.test_functions
        d_elem = np.zeros(len(test_functions))
        for j, test_function in enumerate(test_functions):  # loop over test functions
            integrand = self.generate_integrand(test_function, vert_coords)
            # integrate over element and put in element vector
            d_elem[j] = discretization.integrate_element(integrand)
        return d_elem


class Source(SourceOperator):
    def __init__(self, grid, discretization, f):
        self.grid = grid
        self.discretization = discretization
        self.f = f
        self.d = self.assemble_source_vector()

    def generate_integrand(self, test_function, vert_coords):
        # f
        # weak form:
        # \int_0^L f*v dx
        discretization = self.discretization
        jacobian = discretization.get_jacobian(vert_coords)
        det = np.linalg.det(jacobian)
        f = self.f
        # transform f to function of xieta
        f_xieta = discretization.coordinate_transformation(vert_coords, f)
        # multiply by determinant of jacobian to get integral over local element
        integrand = lambda xieta: f_xieta(xieta)*test_function(xieta)*det
        return integrand


class SolutionOperator():
    """Discrete operator acting on the solution."""
    def __init__(self, grid, discretization, operators):
        self.grid = grid
        self.discretization = discretization
        self.s = self.combine_operators(operators)

    def combine_operators(self, operators):
        s = np.zeros(operators[0].s.shape)
        for idx, operator in enumerate(operators):
            s = s + operator.s
        return s

    def assemble_stiffness_matrix(self):
        """Operates on vertices.

        For each vertex, sum the contributions of allits neighbouring elements. Each vertex has an
        accompanying linear basis function. In 1D this is composed of phi1 operating on its left
        element, and phi0 operating on its right element.
        """
        grid = self.grid
        s = np.zeros((len(grid.xy_vert), len(grid.xy_vert)))  # n = number of vertices
        for i, xy_i in enumerate(grid.xy_elem):  # loop over elements
            # xy_i is center of current element
            elem_vertices = grid.elmat[i]
            s_elem = self.generate_element_matrix(elem_vertices)
            for j in range(len(elem_vertices)):  # loop over equations for vertex coefficients
                # Each equation is associated with one test function.
                # We are now considering the contribution of one element to two different equations (in 1D).
                # Each equation is associated with two elements (in 1D).
                # So the equation will be revisted when considering a different element.
                for k in range(len(elem_vertices)):  # loop over solution basis functions
                    # Each basis function is associated with one vertex.
                    # For each element-equation combination, there are two contributing vertices (in 1D).
                    # Each vertex is associated with two equations and two elements (in 1D).
                    # So the vertex will be revisited three times (in 1D).
                    # From vertex i we have contributions (in 1D):
                    # \int_{x_{i-1}}^{x_{i}} phi0*phi1*c_i + \int_{x_{i-1}}^{x_{i}} phi1*phi1 c_i + \int_{x_{i}}^{x_{i+1}} phi0*phi0 c_i + \int_{x_{i}}^{x_{i+1}} phi1*phi0 c_i
                    s[grid.elmat[i, j], grid.elmat[i, k]] += s_elem[j, k]
                    # first index: equation/test function, second index: vertex coefficient/basis function
        return s

    def generate_element_matrix(self, elem_vertices):
        """Element matrix, operates on elements.

        Matrix should be symmetric. Numerical calculation.
        """
        # get vertex coordinates
        grid = self.grid
        discretization = self.discretization
        vert_coords = np.array([grid.xy_vert[ev] for ev in elem_vertices])
        test_functions = discretization.test_functions
        basis_functions = discretization.basis_functions
        jac = discretization.get_jacobian(vert_coords)  # dxydxieta
        jac_inv = np.linalg.inv(jac)  # dxietadxy
        det = np.linalg.det(jac)
        dphidxieta = discretization.dphidxieta
        dvdxieta = discretization.dvdxieta
        dphidxy = np.matmul(dphidxieta, jac_inv)
        dvdxy = np.matmul(dvdxieta, jac_inv)
        # calculate s_ij
        s_elem = np.zeros((len(test_functions), len(test_functions)))
        for j, test_function in enumerate(basis_functions):  # loop over test functions
            dvjdxy = dvdxy[j]
            for k, basis_function in enumerate(basis_functions):  # loop over solution basis functions
                dphikdxy = dphidxy[k]
                integrand = self.generate_integrand(test_function, basis_function, dvjdxy, dphikdxy, det, vert_coords)
                # integrate over element and put in element matrix
                s_elem[j, k] = discretization.integrate_element(integrand)
        return s_elem


class NaturalBoundary():
    def __init__(self, grid, discretization, bc_types, bc_functions, operators):
        self.grid = grid
        self.discretization = discretization
        self.bc_types = bc_types
        self.bc_functions = bc_functions
        self.b_nat = self.combine_operators(operators)

    def combine_operators(self, operators):
        b_nat = np.zeros(len(self.grid.xy_vert))
        for idx, operator in enumerate(operators):
            b_nat = b_nat + operator.b_nat
        return b_nat

    def generate_natural_boundary_term(self, belem_vertices, lb):
        """Operates on boundary element.

        Natural boundary conditions are implicitly satisfied by the formulation.
        """
        grid = self.grid
        discretization = self.discretization
        bc_types = self.bc_types
        bc_functions = self.bc_functions
        vert_coords = np.array([grid.xy_vert[ev] for ev in belem_vertices])
        # get bc
        bc_type = bc_types[lb]
        bc_function = bc_functions[lb]
        # get test functions
        test_functions_bound = discretization.test_functions_bound
        b_elem = np.zeros(len(test_functions_bound))
        for j, test_function in enumerate(test_functions_bound):  # loop over test functions
            integrand = self.generate_boundary_integrand(test_function, vert_coords, bc_type, bc_function)
            # integrate over element and put in element vector
            b_elem[j] = discretization.integrate_element(integrand, True)
        return b_elem

    def assemble_natural_boundary_vector(self):
        """Operates on vertices."""
        grid = self.grid
        b = np.zeros(len(grid.xy_vert))
        # loop over boundary elements
        for i, xy_i in enumerate(grid.xy_bound):
            # xy_i is center of current boundary element
            belem_vertices = grid.belmat[i]
            lb = grid.loc_bound[i]
            b_elem = self.generate_natural_boundary_term(belem_vertices, lb)
            # assign contributions from boundary element i to every connected vertex (only 1 in 1D)
            for j in range(len(belem_vertices)):
                # each boundary vertex is associated with one test function (in 1D),
                # which is associated with one equation
                b[grid.belmat[i, j]] += b_elem[j]
                # grid.belmat[i,j] is the index of the vertex/test function/equation
        return b


class Diffusion(SolutionOperator, NaturalBoundary):
    # -D*u_xx
    # weak form:
    # -[D*(du/dx)*v]_0^L + \int_0^L D*(du/dx)*(dv/dx) dx
    def __init__(self, grid, discretization, bc_types, bc_functions, D):
        self.grid = grid
        self.discretization = discretization
        self.bc_types = bc_types
        self.bc_functions = bc_functions
        self.coeff = D
        self.s = self.assemble_stiffness_matrix()
        self.b_nat = self.assemble_natural_boundary_vector()

    def generate_integrand(self, test_function, basis_function, dvjdxy, dphikdxy, det, vert_coords):
        """Generate integrand for diffusion.

        This is only one of the integrands, for one of the combinations of test and basis
        functions.
        """
        integrand = lambda xieta: self.coeff*(np.dot(dvjdxy, dphikdxy)).item()*det
        return integrand

    def generate_boundary_integrand(self, test_function, vert_coords, bc_type, bc_function):
        # Since we reduce the order of the diffusion operator through integration by parts,
        # boundary terms appear, which must be added to the equation.
        # since this term will be added to right-hand side, it gets a minus sign
        discretization = self.discretization
        # transform bc_function to function of xieta
        bc_function_xieta, det = discretization.coordinate_transformation_bound(vert_coords, bc_function)
        if bc_type == "neumann":
            integrand = lambda xieta: self.coeff*bc_function_xieta(xieta)*test_function(xieta)*det
        else:
            integrand = lambda xieta: 0
        return integrand


class Reaction(SolutionOperator, NaturalBoundary):
    # R*u
    # weak form:
    # \int_0^L R*u*v dx
    def __init__(self, grid, discretization, bc_types, bc_functions, R):
        self.grid = grid
        self.discretization = discretization
        self.bc_types = bc_types
        self.bc_functions = bc_functions
        self.coeff = R
        self.s = self.assemble_stiffness_matrix()
        self.b_nat = self.assemble_natural_boundary_vector()

    def generate_integrand(self, test_function, basis_function, dvjdxy, dphikdxy, det, vert_coords):
        """Generate integrand for reaction."""
        integrand = lambda xieta: self.coeff*test_function(xieta)*basis_function(xieta)*det
        return integrand

    def generate_boundary_integrand(self, test_function, vert_coords, bc_type, bc_function):
        # the boundary terms are zero for the reaction operator, since there is no integration by parts
        integrand = lambda xieta: 0
        return integrand


class Advection(SolutionOperator, NaturalBoundary):
    # A*u_x
    # weak form:
    # \int_0^L A*(du/dx)*v dx
    def __init__(self, grid, discretization, bc_types, bc_functions, A):
        self.grid = grid
        self.discretization = discretization
        self.bc_types = bc_types
        self.bc_functions = bc_functions
        self.coeff = A
        self.s = self.assemble_stiffness_matrix()
        self.b_nat = self.assemble_natural_boundary_vector()

    def generate_integrand(self, test_function, basis_function, dvjdxy, dphikdxy, det, vert_coords):
        """Generate integrand for linear advection."""
        integrand = lambda xieta: self.coeff*dphikdxy.item()*test_function(xieta)*det
        return integrand

    def generate_boundary_integrand(self, test_function, vert_coords, bc_type, bc_function):
        # the boundary terms are zero for the advection operator, since there is no integration by parts
        integrand = lambda xieta: 0
        return integrand


class Solution():
    def __init__(self, grid, discretization, bc_types, bc_functions, stiffness, source, natural_boundary, xy):
        self.grid = grid
        self.discretization = discretization
        self.bc_types = bc_types
        self.bc_functions = bc_functions
        self.u = self.calculate_solution(stiffness, source, natural_boundary, xy)

    def calculate_solution(self, stiffness, source, natural_boundary, xy):
        grid = self.grid
        discretization = self.discretization
        bc_types = self.bc_types
        bc_functions = self.bc_functions
        s = stiffness.s
        d = source.d
        b_nat = natural_boundary.b_nat

        # now we handle the essential boundary terms (ie dirichlet boundary conditions)

        # theoretical view is to decompose the solution into: u = u_0 + g_tilde
        # so we solve the following equation for u_0:
        # s*u_0 = d + b_nat - u*g_tilde
        # then we set up the homegenous dirichlet problem for u_0
        # this includes setting h[idx1] = 0
        # after linear solve the g vector is added back to the solution, to obtain u
        # below, we instead take a (equivalent) practical approach, in which we
        # just set the values of the boundary nodes to the values of the dirichlet boundary conditions
        # and move their contribution (in the equations for the interior nodes) to the right hand side

        # g is a vector containing set values for nodes lying on dirichlet boundary
        g = np.zeros(len(grid.xy_vert))
        for idx0, xb in enumerate(grid.xy_bound):  # loop over boundary elements
            lb = grid.loc_bound[idx0]
            bc_type = bc_types[lb]
            bc_function = bc_functions[lb]
            for idx1 in grid.belmat[idx0]:  # loop over vertices connected to boundary element
                xv = grid.xy_vert[idx1]  # position of vertex
                if bc_type == "dirichlet":
                    # set value for this boundary node
                    bc_value = bc_function(xv)
                    g[idx1] = bc_value

        # right-hand side contains contributions from source, natural boundary conditions, and dirichlet boundary conditions
        h = d + b_nat - np.matmul(s, g)
        # substracting the latter term just means we move terms in the equations for the interior points to the right hand side
        # these are the terms involving boundary points

        # conduct same loop as before
        # modify stiffness matrix and rhs vector to implement dirichlet boundary conditions
        for idx0, xb in enumerate(grid.xy_bound):  # loop over boundary elements
            lb = grid.loc_bound[idx0]
            bc_type = bc_types[lb]
            for idx1 in grid.belmat[idx0]:  # loop over vertices connected to boundary element
                # xv = grid.xy_vert[idx1]  # position of vertex
                if bc_type == "dirichlet":
                    # eliminate row in stiffness matrix and replace with diagonal 1
                    # this way we get an equation such that 1*boundary_vertex = ...
                    s[idx1] = 0
                    # eliminate column in stiffness matrix
                    # this is possible because we have moved these terms to the right hand side by subtracting np.matmul(s,g) (aka forward substitution)
                    s[:, idx1] = 0
                    s[idx1, idx1] = 1
                    # eliminate row in rhs
                    # this changes the equations for the boundary vertices into 1*boundary_vertex = bc
                    h[idx1] = g[idx1]

        # solve for solution values at vertices
        # these are actually the coefficients associated with the basis
        # functions centered at each grid point
        c = np.linalg.solve(s, h)
        # construct solution at arbitrary locations x, using basis functions
        u = self.construct_solution(grid, discretization, c, xy)
        return u

    def construct_solution(self, grid, discretization, c, sol_locs):
        discretization = self.discretization
        sol = np.zeros(len(sol_locs))
        # loop over solution coordinates
        for idx_sol, sol_loc in enumerate(sol_locs):
            # loop over elements
            for i, xy_i in enumerate(grid.xy_elem):  # xy_i is center of current element
                elem_vertices = grid.elmat[i]
                vert_coords = np.array([grid.xy_vert[ev] for ev in elem_vertices])
                if discretization.check_if_point_in_element(vert_coords, sol_loc):
                    # coordinate is in this element
                    # get basis functions
                    basis_functions_xieta = discretization.basis_functions
                    basis_functions = [discretization.coordinate_transformation_inverse(vert_coords, bfx) for bfx in basis_functions_xieta]
                    # basis_functions = discretization.coordinate_transformation_inverse(vert_coords, basis_functions_xieta)
                    # loop over bounding vertices
                    for j in range(grid.elmat.shape[1]):
                        # we assume the basis functions and the rows of the elmat are ordered correspondingly
                        sol[idx_sol] += c[grid.elmat[i, j]]*basis_functions[j](sol_loc)
                    # due to details of the check it would be possible to double count this sol_loc
                    # so break this loop and move on to next sol_loc
                    break
        return sol
