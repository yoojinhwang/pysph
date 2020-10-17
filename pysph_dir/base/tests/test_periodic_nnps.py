"""Tests for the periodicity algorithms in NNPS"""

# NumPy
import numpy as np

# PySPH imports
from pysph.base.nnps import DomainManager, BoxSortNNPS, LinkedListNNPS, \
    SpatialHashNNPS, ExtendedSpatialHashNNPS
from pysph.base.utils import get_particle_array
from pysph.base.kernels import Gaussian, get_compiled_kernel
import pysph.tools.geometry as G

# PyZoltan CArrays
from cyarray.carray import UIntArray

# Python unit testing framework
import unittest


class PeriodicChannel2DTestCase(unittest.TestCase):
    """Test the periodicity algorithms in NNPS.

    A channel like set-up is used in 2D with fluid particles between
    parallel flat plates. Periodic boundary conditions are imposed
    along the 'x' direction and summation density is used to check for
    the density of the fluid particles.

    """

    def setUp(self):
        # create the particle arrays
        L = 1.0
        n = 100
        dx = L / n
        hdx = 1.5
        _x = np.arange(dx / 2, L, dx)
        self.vol = vol = dx * dx

        # fluid particles
        xx, yy = np.meshgrid(_x, _x)

        x = xx.ravel()
        y = yy.ravel()  # particle positions
        h = np.ones_like(x) * hdx * dx    # smoothing lengths
        m = np.ones_like(x) * vol       # mass
        V = np.zeros_like(x)            # volumes

        fluid = get_particle_array(name='fluid', x=x, y=y, h=h, m=m, V=V)

        # channel particles
        _y = np.arange(L + dx / 2, L + dx / 2 + 10 * dx, dx)
        xx, yy = np.meshgrid(_x, _y)

        xtop = xx.ravel()
        ytop = yy.ravel()

        _y = np.arange(-dx / 2, -dx / 2 - 10 * dx, -dx)
        xx, yy = np.meshgrid(_x, _y)

        xbot = xx.ravel()
        ybot = yy.ravel()

        x = np.concatenate((xtop, xbot))
        y = np.concatenate((ytop, ybot))

        h = np.ones_like(x) * hdx * dx
        m = np.ones_like(x) * vol
        V = np.zeros_like(x)

        channel = get_particle_array(name='channel', x=x, y=y, h=h, m=m, V=V)

        # particles and domain
        self.particles = [fluid, channel]
        self.domain = DomainManager(xmin=0, xmax=L,
                                    periodic_in_x=True)
        self.kernel = get_compiled_kernel(Gaussian(dim=2))

    def _test_periodicity_flags(self):
        "NNPS :: checking for periodicity flags"
        nnps = self.nnps
        domain = self.domain
        self.assertTrue(nnps.is_periodic)

        self.assertTrue(domain.manager.periodic_in_x)
        self.assertTrue(not domain.manager.periodic_in_y)
        self.assertTrue(not domain.manager.periodic_in_z)

    def _test_summation_density(self):
        "NNPS :: testing for summation density"
        fluid, channel = self.particles
        nnps = self.nnps
        kernel = self.kernel

        # get the fluid arrays
        fx, fy, fh, frho, fV, fm = fluid.get(
            'x', 'y', 'h', 'rho', 'V', 'm', only_real_particles=True)

        # initialize the fluid density and volume
        frho[:] = 0.0
        fV[:] = 0.0

        # compute density on the fluid
        nbrs = UIntArray()
        for i in range(fluid.num_real_particles):
            hi = fh[i]

            # compute density from the fluid from the source arrays
            nnps.get_nearest_particles(src_index=0, dst_index=0,
                                       d_idx=i, nbrs=nbrs)
            nnbrs = nbrs.length

            # the source arrays. First source is also the fluid
            sx, sy, sh, sm = fluid.get('x', 'y', 'h', 'm',
                                       only_real_particles=False)

            for indexj in range(nnbrs):
                j = nbrs[indexj]
                hij = 0.5 * (hi + sh[j])

                frho[i] += sm[j] * \
                    kernel.kernel(fx[i], fy[i], 0.0, sx[j], sy[j], 0.0, hij)
                fV[i] += kernel.kernel(fx[i], fy[i], 0.0,
                                       sx[j], sy[j], 0.0, hij)

            # compute density from the channel
            nnps.get_nearest_particles(
                src_index=1, dst_index=0, d_idx=i, nbrs=nbrs)
            nnbrs = nbrs.length

            sx, sy, sh, sm = channel.get(
                'x', 'y', 'h', 'm', only_real_particles=False)

            for indexj in range(nnbrs):
                j = nbrs[indexj]

                hij = 0.5 * (hi + sh[j])

                frho[i] += sm[j] * \
                    kernel.kernel(fx[i], fy[i], 0.0, sx[j], sy[j], 0.0, hij)
                fV[i] += kernel.kernel(fx[i], fy[i], 0.0,
                                       sx[j], sy[j], 0.0, hij)

            # check the number density and density by summation
            voli = 1. / fV[i]
            self.assertAlmostEqual(voli, self.vol, 6)
            self.assertAlmostEqual(frho[i], fm[i] / voli, 6)


class PeriodicChannel2DBoxSort(PeriodicChannel2DTestCase):
    def setUp(self):
        PeriodicChannel2DTestCase.setUp(self)
        self.nnps = BoxSortNNPS(
            dim=2, particles=self.particles,
            domain=self.domain,
            radius_scale=self.kernel.radius_scale)

    def test_periodicity_flags(self):
        "BoxSortNNPS :: test periodicity flags"
        self._test_periodicity_flags()

    def test_summation_density(self):
        "BoxSortNNPS :: test summation density"
        self._test_summation_density()


class PeriodicChannel2DLinkedList(PeriodicChannel2DTestCase):
    def setUp(self):
        PeriodicChannel2DTestCase.setUp(self)
        self.nnps = LinkedListNNPS(
            dim=2, particles=self.particles,
            domain=self.domain,
            radius_scale=self.kernel.radius_scale)

    def test_periodicity_flags(self):
        "LinkedListNNPS :: test periodicity flags"
        self._test_periodicity_flags()

    def test_summation_density(self):
        "LinkedListNNPS :: test summation density"
        self._test_summation_density()

    def test_add_property_after_creation_works(self):
        # Given
        particles = self.particles
        fluid = particles[0]

        # When
        fluid.add_property('junk')

        # Then
        self.nnps.update_domain()
        self._test_summation_density()


class PeriodicChannel2DSpatialHash(PeriodicChannel2DTestCase):
    def setUp(self):
        PeriodicChannel2DTestCase.setUp(self)
        self.nnps = SpatialHashNNPS(
            dim=2, particles=self.particles,
            domain=self.domain,
            radius_scale=self.kernel.radius_scale)

    def test_periodicity_flags(self):
        "SpatialHashNNPS :: test periodicity flags"
        self._test_periodicity_flags()

    def test_summation_density(self):
        "SpatialHashNNPS :: test summation density"
        self._test_summation_density()


class PeriodicChannel2DExtendedSpatialHash(PeriodicChannel2DTestCase):
    def setUp(self):
        PeriodicChannel2DTestCase.setUp(self)
        self.nnps = ExtendedSpatialHashNNPS(
            dim=2, particles=self.particles,
            domain=self.domain,
            radius_scale=self.kernel.radius_scale)

    def test_periodicity_flags(self):
        self._test_periodicity_flags()

    def test_summation_density(self):
        self._test_summation_density()


class TestPeriodicChannel3D(unittest.TestCase):

    def setUp(self):
        self.l = l = 1.0
        n = 20
        dx = l / n
        hdx = 1.5

        x, y, z = G.get_3d_block(dx, l, l, l)
        h = np.ones_like(x) * hdx * dx
        m = np.ones_like(x) * dx * dx * dx
        V = np.zeros_like(x)
        fluid = get_particle_array(name='fluid', x=x, y=y, z=z, h=h, m=m, V=V)

        x, y = G.get_2d_block(dx, l, l)
        z = np.ones_like(x) * (l + 5 * dx) / 2.0
        z = np.concatenate([z, -z])
        x = np.tile(x, 2)
        y = np.tile(y, 2)
        m = np.ones_like(x) * dx * dx * dx
        h = np.ones_like(x) * hdx * dx
        V = np.zeros_like(x)
        channel = get_particle_array(
            name='channel', x=x, y=y, z=z, h=h, m=m, V=V)

        self.particles = [fluid, channel]
        self.kernel = get_compiled_kernel(Gaussian(dim=3))

    def _test_periodic_flags(self, bool1, bool2, bool3):
        nnps = self.nnps
        domain = self.domain.manager
        self.assertTrue(nnps.is_periodic)
        self.assertTrue(domain.periodic_in_x == bool1)
        self.assertTrue(domain.periodic_in_y == bool2)
        self.assertTrue(domain.periodic_in_z == bool3)


class TestPeriodicXYZ3D(TestPeriodicChannel3D):

    def setUp(self):
        TestPeriodicChannel3D.setUp(self)
        l = self.l
        self.domain = DomainManager(
            xmin=-l / 2.0, xmax=l / 2.0, ymin=-l / 2.0, ymax=l / 2.0,
            zmin=-l / 2.0, zmax=l / 2.0, periodic_in_x=True,
            periodic_in_y=True, periodic_in_z=True)
        self.nnps = LinkedListNNPS(
            dim=3, particles=self.particles, domain=self.domain,
            radius_scale=self.kernel.radius_scale)

    def test_periodicity_flags(self):
        self._test_periodic_flags(True, True, True)


class TestPeriodicZ3D(TestPeriodicChannel3D):

    def setUp(self):
        TestPeriodicChannel3D.setUp(self)
        l = self.l
        self.domain = DomainManager(
            zmin=-l / 2.0, zmax=l / 2.0, periodic_in_z=True)
        self.nnps = LinkedListNNPS(
            dim=3, particles=self.particles, domain=self.domain,
            radius_scale=self.kernel.radius_scale)

    def test_periodicity_flags(self):
        self._test_periodic_flags(False, False, True)


class TestPeriodicXY3D(TestPeriodicChannel3D):

    def setUp(self):
        TestPeriodicChannel3D.setUp(self)
        l = self.l
        self.domain = DomainManager(
            xmin=-l / 2.0, xmax=l / 2.0, ymin=-l / 2.0, ymax=l / 2.0,
            periodic_in_x=True, periodic_in_y=True)
        self.nnps = LinkedListNNPS(
            dim=3, particles=self.particles, domain=self.domain,
            radius_scale=self.kernel.radius_scale)

    def test_periodicity_flags(self):
        self._test_periodic_flags(True, True, False)


if __name__ == '__main__':
    unittest.main()
