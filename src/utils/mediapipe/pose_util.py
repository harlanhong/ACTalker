import math

import numpy as np
from scipy.spatial.transform import Rotation as R
import pdb

def create_perspective_matrix(aspect_ratio):
    kDegreesToRadians = np.pi / 180.
    near = 1
    far = 10000
    perspective_matrix = np.zeros(16, dtype=np.float32)

    # Standard perspective projection matrix calculations.
    f = 1.0 / np.tan(kDegreesToRadians * 63 / 2.)

    denom = 1.0 / (near - far)
    perspective_matrix[0] = f / aspect_ratio
    perspective_matrix[5] = f
    perspective_matrix[10] = (near + far) * denom
    perspective_matrix[11] = -1.
    perspective_matrix[14] = 1. * far * near * denom

    # If the environment's origin point location is in the top left corner,
    # then skip additional flip along Y-axis is required to render correctly.

    perspective_matrix[5] *= -1.
    return perspective_matrix


def project_points(points_3d, transformation_matrix, pose_vectors, image_shape):
    P = create_perspective_matrix(image_shape[1] / image_shape[0]).reshape(4, 4).T
    L, N, _ = points_3d.shape

    #
    projected_points = np.zeros((L, N, 2))
    for i in range(L):
        points_3d_frame = points_3d[i]
        ones = np.ones((points_3d_frame.shape[0], 1))
        points_3d_homogeneous = np.hstack([points_3d_frame, ones])  
        transformed_points = points_3d_homogeneous @ (transformation_matrix @ euler_and_translation_to_matrix(pose_vectors[i][:3], pose_vectors[i][3:])).T @ P
        projected_points_frame = transformed_points[:, :2] / transformed_points[:, 3, np.newaxis] # -1 ~ 1
        projected_points_frame[:, 0] = (projected_points_frame[:, 0] + 1) * 0.5 #* image_shape[1] 
        projected_points_frame[:, 1]  = (projected_points_frame[:, 1] + 1) * 0.5 #* image_shape[0]
        projected_points[i] = projected_points_frame
    return projected_points.astype(np.float32)

def invert_projection(projected_points, transformation_matrix, pose_vectors, image_shape):
    P = create_perspective_matrix(image_shape[1] / image_shape[0]).reshape(4, 4).T
    P_inv = np.linalg.inv(P)
    
    L, N, _ = projected_points.shape
    points_3d = np.zeros((L, N, 3))
    
    for i in range(L):
        projected_points_frame = projected_points[i]
        
        # De-normalize
        projected_points_frame[:, 0] = (projected_points_frame[:, 0] / 0.5) - 1
        projected_points_frame[:, 1] = (projected_points_frame[:, 1] / 0.5) - 1
        
        # Convert to homogeneous coordinates
        ones = np.ones((projected_points_frame.shape[0], 1))
        projected_points_homogeneous = np.hstack([projected_points_frame, np.ones((N, 1))])
        
        # Apply inverse perspective transformation
        transformed_points = projected_points_homogeneous @ P_inv.T
        
        # Apply inverse pose transformation
        transformation_inv = np.linalg.inv(transformation_matrix @ euler_and_translation_to_matrix(pose_vectors[i][:3], pose_vectors[i][3:]))
        points_3d_homogeneous = transformed_points @ transformation_inv.T
        
        # Convert back to non-homogeneous coordinates
        points_3d_frame = points_3d_homogeneous[:, :3] / points_3d_homogeneous[:, 3, np.newaxis]
        points_3d[i] = points_3d_frame
    
    return points_3d.astype(np.float32)
def project_points_with_trans(points_3d, transformation_matrix, image_shape):
    P = create_perspective_matrix(image_shape[1] / image_shape[0]).reshape(4, 4).T
    L, N, _ = points_3d.shape
    projected_points = np.zeros((L, N, 2))
    for i in range(L):
        points_3d_frame = points_3d[i]
        ones = np.ones((points_3d_frame.shape[0], 1))
        points_3d_homogeneous = np.hstack([points_3d_frame, ones])  
        
        # transformed_points = points_3d_homogeneous @ transformation_matrix[i].T @ P
        transformed_points = points_3d_homogeneous @ transformation_matrix.T @ P
        
        projected_points_frame = transformed_points[:, :2] / transformed_points[:, 3, np.newaxis] # -1 ~ 1
        projected_points_frame[:, 0] = (projected_points_frame[:, 0] + 1) * 0.5 #* image_shape[1] 
        projected_points_frame[:, 1]  = (projected_points_frame[:, 1] + 1) * 0.5 #* image_shape[0]
        projected_points[i] = projected_points_frame

    return projected_points.astype(np.float32)


def euler_and_translation_to_matrix(euler_angles, translation_vector):
    rotation = R.from_euler('xyz', euler_angles, degrees=True)
    rotation_matrix = rotation.as_matrix()
    
    matrix = np.eye(4)
    matrix[:3, :3] = rotation_matrix
    matrix[:3, 3] = translation_vector
    
    return matrix


def matrix_to_euler_and_translation(matrix):
    rotation_matrix = matrix[:3, :3]
    translation_vector = matrix[:3, 3]
    rotation = R.from_matrix(rotation_matrix)
    euler_angles = rotation.as_euler('xyz', degrees=True)
    return euler_angles, translation_vector


def smooth_pose_seq(pose_seq, window_size=5):
    smoothed_pose_seq = np.zeros_like(pose_seq)

    for i in range(len(pose_seq)):
        start = max(0, i - window_size // 2)
        end = min(len(pose_seq), i + window_size // 2 + 1)
        smoothed_pose_seq[i] = np.mean(pose_seq[start:end], axis=0)

    return smoothed_pose_seq