import React from 'react';
import { render } from '@testing-library/react-native';
import { Text } from 'react-native';
import { Card } from '../src/Card';

describe('Card', () => {
  it('renders children', () => {
    const { getByText } = render(
      <Card>
        <Text>Card Content</Text>
      </Card>,
    );
    expect(getByText('Card Content')).toBeTruthy();
  });

  it('renders multiple children', () => {
    const { getByText } = render(
      <Card>
        <Text>First Child</Text>
        <Text>Second Child</Text>
      </Card>,
    );
    expect(getByText('First Child')).toBeTruthy();
    expect(getByText('Second Child')).toBeTruthy();
  });

  it('applies padding by default (padded=true)', () => {
    const { UNSAFE_getByType } = render(
      <Card>
        <Text>Content</Text>
      </Card>,
    );
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const flatStyle = Array.isArray(view.props.style)
      ? Object.assign({}, ...view.props.style.filter(Boolean))
      : view.props.style;
    expect(flatStyle.padding).toBeDefined();
  });

  it('does not apply padding when padded=false', () => {
    const { UNSAFE_getByType } = render(
      <Card padded={false}>
        <Text>Content</Text>
      </Card>,
    );
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const styleArray = view.props.style;
    // When padded=false, the padding style object should be falsy in the array
    const flatStyle = Array.isArray(styleArray)
      ? Object.assign({}, ...styleArray.filter(Boolean))
      : styleArray;
    expect(flatStyle.padding).toBeUndefined();
  });

  it('applies border and borderRadius', () => {
    const { UNSAFE_getByType } = render(
      <Card>
        <Text>Content</Text>
      </Card>,
    );
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const flatStyle = Array.isArray(view.props.style)
      ? Object.assign({}, ...view.props.style.filter(Boolean))
      : view.props.style;
    expect(flatStyle.borderWidth).toBe(1);
    expect(flatStyle.borderRadius).toBeDefined();
  });

  it('accepts custom styles', () => {
    const { UNSAFE_getByType } = render(
      <Card style={{ marginTop: 20 }}>
        <Text>Content</Text>
      </Card>,
    );
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const flatStyle = Array.isArray(view.props.style)
      ? Object.assign({}, ...view.props.style.filter(Boolean))
      : view.props.style;
    expect(flatStyle.marginTop).toBe(20);
  });
});
