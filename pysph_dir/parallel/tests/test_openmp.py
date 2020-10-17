""" Module to run the example files and report their success/failure results

Add a function to the ExampleTest class corresponding to an example script to
be tested.
This is done till better strategy for parallel testing is implemented

"""

from pytest import mark
from .example_test_case import ExampleTestCase, get_example_script
from pysph.base.nnps import get_number_of_threads


@mark.skipif(get_number_of_threads() == 1, reason= "N_threads=1; OpenMP does not seem available.")
class TestOpenMPExamples(ExampleTestCase):

    @mark.slow
    def test_3Ddam_break_example(self):
        dt = 2e-5; tf = 13*dt
        serial_kwargs = dict(
            timestep=dt, tf=tf, pfreq=100, test=None
        )
        extra_parallel_kwargs = dict(openmp=None)
        # Note that we set nprocs=1 here since we do not want
        # to run this with mpirun.
        self.run_example(
            get_example_script('sphysics/dambreak_sphysics.py'),
            nprocs=1, atol=1e-14,
            serial_kwargs=serial_kwargs,
            extra_parallel_kwargs=extra_parallel_kwargs
        )

    @mark.slow
    def test_elliptical_drop_example(self):
        tf = 0.0076*0.25
        serial_kwargs = dict(kernel='CubicSpline', tf=tf)
        extra_parallel_kwargs = dict(openmp=None)
        # Note that we set nprocs=1 here since we do not want
        # to run this with mpirun.
        self.run_example(
            'elliptical_drop.py', nprocs=1, atol=1e-14,
            serial_kwargs=serial_kwargs,
            extra_parallel_kwargs=extra_parallel_kwargs
        )

    def test_ldcavity_example(self):
        dt=1e-4; tf=200*dt
        serial_kwargs = dict(timestep=dt, tf=tf, pfreq=500)
        extra_parallel_kwargs = dict(openmp=None)
        # Note that we set nprocs=1 here since we do not want
        # to run this with mpirun.
        self.run_example(
            'cavity.py', nprocs=1, atol=1e-14,
            serial_kwargs=serial_kwargs,
            extra_parallel_kwargs=extra_parallel_kwargs
        )
