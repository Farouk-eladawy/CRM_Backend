import api from '../client';
import type { RepPortalJob, RepProfile, PortalNotification } from '../../types';

export const repPortalApi = {
  getJobs(date: string) {
    return api.get<RepPortalJob[]>('/rep-portal/jobs', { params: { date } });
  },

  getJobHistory(dateFrom: string, dateTo: string) {
    return api.get<RepPortalJob[]>('/rep-portal/jobs/history', {
      params: { dateFrom, dateTo },
    });
  },

  updateJobStatus(jobId: string, status: string, latitude?: number, longitude?: number) {
    return api.patch(`/rep-portal/jobs/${jobId}/status`, { status, latitude, longitude });
  },

  submitNoShow(jobId: string, formData: FormData) {
    return api.post(`/rep-portal/jobs/${jobId}/no-show`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getNotifications() {
    return api.get<PortalNotification[]>('/rep-portal/notifications');
  },

  markNotificationRead(notificationId: string) {
    return api.patch(`/rep-portal/notifications/${notificationId}/read`);
  },

  markAllNotificationsRead() {
    return api.patch('/rep-portal/notifications/read-all');
  },

  getProfile() {
    return api.get<RepProfile>('/rep-portal/profile');
  },
};
