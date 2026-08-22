import { AppRegistry } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import { setFirebaseMessaging, setBackgroundMessageHandler } from '@itour/shared';
import { App } from './src/App';
import { name as appName } from './app.json';

// Register background message handler (must be outside React components)
setFirebaseMessaging(messaging);
setBackgroundMessageHandler();

AppRegistry.registerComponent(appName, () => App);
