import React, { useState } from 'react';
import { View, Text, Image, StyleSheet, ScrollView, Alert } from 'react-native';
import type { StackScreenProps } from '@react-navigation/stack';
import {
  repPortalApi,
  useGPS,
  takePhoto as capturePhoto,
  getColors,
  spacing,
  typography,
  borderRadius,
  useT,
} from '@itour/shared';
import { Button, Card } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Props = StackScreenProps<RootStackParamList, 'NoShow'>;

export function NoShowScreen({ route, navigation }: Props) {
  const { jobId } = route.params;
  const colors = getColors();
  const t = useT();
  const { captureGPS, loading: gpsLoading } = useGPS();
  const [photos, setPhotos] = useState<{ uri: string; fileName: string; type: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const takePhoto = async () => {
    if (photos.length >= 2) return;

    const result = await capturePhoto({ quality: 0.8, maxWidth: 1280, maxHeight: 1280 });
    if (result) {
      setPhotos((prev) => [
        ...prev,
        {
          uri: result.uri,
          fileName: result.fileName,
          type: result.type,
        },
      ]);
    }
  };

  const removePhoto = (index: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (photos.length < 2) {
      Alert.alert(t('common.error'), t('driver.photosRequired'));
      return;
    }

    setSubmitting(true);
    try {
      const gps = await captureGPS();

      const formData = new FormData();
      photos.forEach((photo) => {
        formData.append('images', {
          uri: photo.uri,
          name: photo.fileName,
          type: photo.type,
        } as any);
      });
      formData.append('latitude', String(gps.lat));
      formData.append('longitude', String(gps.lng));

      await repPortalApi.submitNoShow(jobId, formData);
      Alert.alert(t('common.success'), '', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (err: any) {
      Alert.alert(t('common.error'), err?.message || t('common.error'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]}>
      <Card style={styles.card}>
        <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[2] }]}>
          {t('driver.photosRequired')}
        </Text>
        <Text style={[typography.caption, { color: colors.mutedForeground, marginBottom: spacing[3] }]}>
          Take 2 photos as evidence of no-show. GPS location will be captured automatically.
        </Text>

        <View style={styles.photosRow}>
          {photos.map((photo, index) => (
            <View key={index} style={styles.photoContainer}>
              <Image source={{ uri: photo.uri }} style={styles.photo} />
              <Button
                title="X"
                variant="destructive"
                size="sm"
                onPress={() => removePhoto(index)}
                style={styles.removeBtn}
              />
            </View>
          ))}

          {photos.length < 2 && (
            <Button
              title={t('driver.takePhoto')}
              variant="outline"
              onPress={takePhoto}
              style={styles.addPhotoBtn}
            />
          )}
        </View>
      </Card>

      <View style={styles.actions}>
        <Button
          title={t('driver.submitNoShow')}
          onPress={handleSubmit}
          loading={submitting || gpsLoading}
          disabled={photos.length < 2}
          variant="destructive"
          size="lg"
        />
        <Button
          title={t('common.cancel')}
          variant="ghost"
          onPress={() => navigation.goBack()}
          size="lg"
          style={{ marginTop: spacing[2] }}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  card: {
    marginHorizontal: spacing[4],
    marginTop: spacing[4],
  },
  photosRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
  },
  photoContainer: {
    position: 'relative',
  },
  photo: {
    width: 140,
    height: 140,
    borderRadius: borderRadius.lg,
  },
  removeBtn: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 28,
    height: 28,
    paddingHorizontal: 0,
  },
  addPhotoBtn: {
    width: 140,
    height: 140,
  },
  actions: {
    padding: spacing[4],
    paddingBottom: spacing[10],
  },
});
