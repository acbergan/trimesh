try:
    from . import generic as g
except BaseException:
    import generic as g


class VoxelTest(g.unittest.TestCase):

    def test_voxel(self):
        """
        Test that voxels work at all
        """
        for m in [g.get_mesh('featuretype.STL'),
                  g.trimesh.primitives.Box(),
                  g.trimesh.primitives.Sphere()]:
            for pitch in [.1, .1 - g.tol.merge]:
                v = m.voxelized(pitch)

                assert len(v.matrix.shape) == 3
                assert v.shape == v.matrix.shape
                assert v.volume > 0.0

                assert v.origin.shape == (3,)
                assert isinstance(v.pitch, float)
                assert g.np.isfinite(v.pitch)

                assert isinstance(v.filled_count, int)
                assert v.filled_count > 0

                box = v.as_boxes(solid=False)
                boxF = v.as_boxes(solid=True)

                assert isinstance(box, g.trimesh.Trimesh)
                assert abs(boxF.volume - v.volume) < g.tol.merge

                assert g.trimesh.util.is_shape(v.points, (-1, 3))

                assert len(v.sparse_solid) > len(v.sparse_surface)

                assert g.np.all(v.is_filled(v.points))

                outside = m.bounds[1] + m.scale
                assert not v.is_filled(outside)

                try:
                    cubes = v.marching_cubes
                    assert cubes.area > 0.0
                except ImportError:
                    g.log.info('no skimage, skipping marching cubes test')

            g.log.info('Mesh volume was %f, voxelized volume was %f',
                       m.volume,
                       v.volume)

    def test_marching(self):
        """
        Test marching cubes on a matrix
        """
        try:
            from skimage import measure  # NOQA
        except ImportError:
            g.log.warn('no skimage, skipping marching cubes test')
            return

        # make sure offset is correct
        matrix = g.np.ones((3, 3, 3), dtype=g.np.bool)
        mesh = g.trimesh.voxel.matrix_to_marching_cubes(
            matrix=matrix,
            pitch=1.0,
            origin=g.np.zeros(3))
        assert mesh.is_watertight

        mesh = g.trimesh.voxel.matrix_to_marching_cubes(
            matrix=matrix,
            pitch=3.0,
            origin=g.np.zeros(3))
        assert mesh.is_watertight

    def test_marching_points(self):
        """
        Try marching cubes on points
        """
        try:
            from skimage import measure  # NOQA
        except ImportError:
            g.log.warn('no skimage, skipping marching cubes test')
            return

        # get some points on the surface of an icosahedron
        points = g.trimesh.creation.icosahedron().sample(1000)
        # make the pitch proportional to scale
        pitch = points.ptp(axis=0).min() / 10
        # run marching cubes
        mesh = g.trimesh.voxel.points_to_marching_cubes(
            points=points, pitch=pitch)

        # mesh should have faces
        assert len(mesh.faces) > 0
        # mesh should be roughly centered
        assert (mesh.bounds[0] < -.5).all()
        assert (mesh.bounds[1] > .5).all()

    def test_local(self):
        """
        Try calling local voxel functions
        """
        mesh = g.trimesh.creation.box()

        # it should have some stuff
        voxel = g.trimesh.voxel.local_voxelize(
            mesh=mesh,
            point=[.5, .5, .5],
            pitch=.1,
            radius=5,
            fill=True)

        assert len(voxel[0].shape) == 3

        # try it when it definitely doesn't hit anything
        empty = g.trimesh.voxel.local_voxelize(
            mesh=mesh,
            point=[10, 10, 10],
            pitch=.1,
            radius=5,
            fill=True)
        # shouldn't have hit anything
        assert len(empty[0]) == 0

        # try it when it is in the center of a volume
        g.trimesh.voxel.local_voxelize(
            mesh=mesh,
            point=[0, 0, 0],
            pitch=.1,
            radius=2,
            fill=True)

    def test_points_to_from_indices(self):
        # indices = (points - origin) / pitch
        points = [[0, 0, 0], [0.04, 0.55, 0.39]]
        origin = [0, 0, 0]
        pitch = 0.1
        indices = [[0, 0, 0], [0, 6, 4]]

        # points -> indices
        indices2 = g.trimesh.voxel.points_to_indices(
            points=points, origin=origin, pitch=pitch)

        g.np.testing.assert_allclose(indices, indices2, atol=0, rtol=0)

        # indices -> points
        points2 = g.trimesh.voxel.indices_to_points(indices=indices,
                                                    origin=origin,
                                                    pitch=pitch)
        g.np.testing.assert_allclose(g.np.array(indices) * pitch + origin,
                                     points2,
                                     atol=0,
                                     rtol=0)
        g.np.testing.assert_allclose(points,
                                     points2,
                                     atol=pitch / 2 * 1.01,
                                     rtol=0)

        # indices -> points -> indices (this must be consistent)
        points2 = g.trimesh.voxel.indices_to_points(indices=indices,
                                                    origin=origin,
                                                    pitch=pitch)
        indices2 = g.trimesh.voxel.points_to_indices(points=points2,
                                                     origin=origin,
                                                     pitch=pitch)
        g.np.testing.assert_allclose(indices, indices2, atol=0, rtol=0)

    def test_as_boxes(self):
        voxel = g.trimesh.voxel

        pitch = 0.1
        origin = (0, 0, 0)

        matrix = g.np.eye(9, dtype=g.np.bool).reshape((-1, 3, 3))
        centers = voxel.matrix_to_points(matrix=matrix,
                                         pitch=pitch,
                                         origin=origin)
        v = voxel.Voxel(matrix=matrix,
                        pitch=pitch,
                        origin=origin)

        boxes1 = v.as_boxes()
        boxes2 = voxel.multibox(centers, pitch)
        colors = [g.trimesh.visual.DEFAULT_COLOR] * matrix.sum() * 12
        for boxes in [boxes1, boxes2]:
            g.np.testing.assert_allclose(
                boxes.visual.face_colors, colors, atol=0, rtol=0)

        # check assigning a single color
        color = [255, 0, 0, 255]
        boxes1 = v.as_boxes(colors=color)
        boxes2 = voxel.multibox(centers=centers,
                                pitch=pitch,
                                colors=color)
        colors = g.np.array([color] * len(centers) * 12)
        for boxes in [boxes1, boxes2]:
            g.np.testing.assert_allclose(
                boxes.visual.face_colors, colors, atol=0, rtol=0)

        # check matrix colors
        colors = color * g.np.ones(g.np.append(v.shape, 4),
                                   dtype=g.np.uint8)
        boxes = v.as_boxes(colors=colors)
        assert g.np.allclose(
            boxes.visual.face_colors, color, atol=0, rtol=0)

    def _test_equiv(self, v0, v1, query_points):
        def array_as_set(array2d):
            return set(tuple(x) for x in array2d)

        self.assertEqual(v0.shape, v1.shape)
        self.assertEqual(v0.filled_count, v1.filled_count)
        self.assertEqual(v0.volume, v1.volume)
        g.np.testing.assert_equal(v0.matrix, v1.matrix)
        # points will be in different order, but should contain same coords
        g.np.testing.assert_equal(
            array_as_set(v0.points), array_as_set(v1.points))
        g.np.testing.assert_equal(v0.origin, v1.origin)
        g.np.testing.assert_equal(v0.pitch, v1.pitch)
        for qp in query_points:
            g.np.testing.assert_equal(
                v0.point_to_index(qp), v1.point_to_index(qp))
            g.np.testing.assert_equal(v0.is_filled(qp), v1.is_filled(qp))

    def test_transposed(self):
        voxel = g.trimesh.voxel
        matrix = g.np.random.uniform(size=(3, 4, 5)) > 0.5
        axes = g.np.array((2, 0, 1))
        origin = g.np.array([0, 1, 2])
        v = voxel.Voxel(matrix, pitch=1.0, origin=origin)
        vt = v.transpose(axes)
        vt2 = voxel.Voxel(
            matrix.transpose(axes), pitch=1.0, origin=origin[axes])
        query_points = g.np.random.uniform(size=(20, 3), high=5)
        self._test_equiv(vt, vt2, query_points)
        self._test_equiv(vt.to_dense(), vt2.to_dense(), query_points)
        axes2 = g.np.array((1, 0, 2))
        self._test_equiv(
            vt.transpose(axes2), vt2.transpose(axes2), query_points)
        vt3 = voxel.Voxel(
            matrix.transpose(axes).transpose(axes2),
            pitch=1.0,
            origin=origin[axes][axes2])
        self._test_equiv(vt.transpose(axes2), vt3, query_points)

    def test_rle(self):
        from trimesh import rle
        np = g.np
        voxel = g.trimesh.voxel
        pitch = 1
        shape = (4, 4, 4)
        origin = g.np.zeros((3,))
        rle_obj = rle.RunLengthEncoding(np.array([
            0, 8, 1, 40, 0, 16], dtype=np.uint8))
        brle_obj = rle.BinaryRunLengthEncoding(np.array([
            8, 40, 16], dtype=np.uint8))
        v_rle = voxel.VoxelRle(rle_obj, pitch, origin, shape)
        self.assertEqual(v_rle.filled_count, 40)
        np.testing.assert_equal(
            v_rle.matrix, np.reshape([0]*8 + [1]*40 + [0]*16, shape))

        v_brle = voxel.VoxelRle(brle_obj, pitch, origin, shape)
        query_points = np.random.uniform(size=(100, 3), high=4)
        self._test_equiv(v_rle, v_brle, query_points)


if __name__ == '__main__':
    g.trimesh.util.attach_to_log()
    g.unittest.main()
