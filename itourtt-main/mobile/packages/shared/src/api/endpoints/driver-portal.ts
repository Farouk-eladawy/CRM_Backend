import api from '../client';
import type { DriverPortalJob, DriverProfile, PortalNotification } from '../../types';

export const driverPortalApi = {
  getJobs(date: string) {
    return api.get<DriverPortalJob[]>('/driver-portal/jobs', { params: { date } });
  },

  getJobHistory(dateFrom: string, dateTo: string) {
    return api.get<DriverPortalJob[]>('/driver-portal/jobs/history', {
      params: { dateFrom, dateTo },
    });
  },

  updateJobStatus(jobId: string, status: string, latitude?: number, longitude?: number) {
    return api.patch(`/driver-portal/jobs/${jobId}/status`, { status, latitude, longitude });
  },

  markCollection(jobId: string) {
    return api.patch(`/driver-portal/jobs/${jobId}/collection`, { collected: true });
  },

  submitNoShow(jobId: string, formData: FormData) {
    return api.post(`/driver-portal/jobs/${jobId}/no-show`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getNotifications() {
    return api.get<PortalNotification[]>('/driver-portal/notifications');
  },

  markNotificationRead(notificationId: string) {
    return api.patch(`/driver-portal/notifications/${notificationId}/read`);
  },

  markAllNotificationsRead() {
    return api.patch('/driver-portal/notifications/read-all');
  },

  getProfile() {
    return api.get<DriverProfile>('/driver-portal/profile');
  },
};
