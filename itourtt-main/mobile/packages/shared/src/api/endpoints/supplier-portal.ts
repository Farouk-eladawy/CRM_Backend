import api from '../client';
import type { SupplierPortalJob, SupplierProfile } from '../../types';

export const supplierPortalApi = {
  getJobs(date: string) {
    return api.get<SupplierPortalJob[]>('/supplier-portal/jobs', { params: { date } });
  },

  completeJob(jobId: string, notes?: string) {
    return api.patch(`/supplier-portal/jobs/${jobId}/complete`, { notes });
  },

  getProfile() {
    return api.get<SupplierProfile>('/supplier-portal/profile');
  },
};
