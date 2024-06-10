import numpy as np
from sklearn.cluster import KMeans
from scipy.sparse.csgraph import laplacian
from scipy.spatial import cKDTree

class SpectralBridges:
    def __init__(self, n_classes):
        self.n_classes = n_classes

    def fit(self, X, n_nodes, M=1e4):
        kmeans = KMeans(n_clusters=n_nodes).fit(X)

        affinity = np.empty((n_nodes, n_nodes))

        X_centered = [X[kmeans.labels_ == i] - kmeans.cluster_centers_[i] for i in range(n_nodes)]

        counts = np.array([X_centered[i].shape[0] for i in range(n_nodes)])
        counts = counts[np.newaxis, :] + counts[:, np.newaxis]

        segments = kmeans.cluster_centers_[np.newaxis, :] - kmeans.cluster_centers_[:, np.newaxis]
        dists = np.einsum('ijk,ijk->ij', segments, segments)
        np.fill_diagonal(dists, 1)

        for i in range(n_nodes):
            projs = np.dot(X_centered[i], segments[i].T)
            affinity[i] = np.maximum(projs, 0).sum(axis=0)

        affinity = np.power((affinity + affinity.T) / (counts * dists), .5)
        affinity -= .5 * affinity.max()

        q1 = np.quantile(affinity, .25)
        q3 = np.quantile(affinity, .75)

        gamma = np.log(M) / (q3 - q1)
        affinity = np.exp(gamma * affinity)

        L = laplacian(affinity, normed=True)

        _, eigvecs = np.linalg.eigh(L)
        eigvecs = eigvecs[:, :self.n_classes]
        eigvecs /= np.linalg.norm(eigvecs, axis=1)[:, np.newaxis]
        labels = KMeans(n_clusters=self.n_classes).fit_predict(eigvecs)

        self.clusters = [kmeans.cluster_centers_[labels == i] for i in range(self.n_classes)]

    def predict(self, x):
        min_dists = np.array([cKDTree(cluster).query(x, 1)[0] for cluster in self.clusters])
        return min_dists.argmin(axis=0)