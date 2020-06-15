/* Generated by the protocol buffer compiler.  DO NOT EDIT! */
/* Generated from: constants.proto */

/* Do not generate deprecated warnings for self */
#ifndef PROTOBUF_C__NO_DEPRECATED
#define PROTOBUF_C__NO_DEPRECATED
#endif

#include "constants.pb-c.h"
static const ProtobufCEnumValue status__enum_values_by_number[8] =
{
  { "Success", "STATUS__Success", 0 },
  { "InvalidSecScheme", "STATUS__InvalidSecScheme", 1 },
  { "InvalidProto", "STATUS__InvalidProto", 2 },
  { "TooManySessions", "STATUS__TooManySessions", 3 },
  { "InvalidArgument", "STATUS__InvalidArgument", 4 },
  { "InternalError", "STATUS__InternalError", 5 },
  { "CryptoError", "STATUS__CryptoError", 6 },
  { "InvalidSession", "STATUS__InvalidSession", 7 },
};
static const ProtobufCIntRange status__value_ranges[] = {
{0, 0},{0, 8}
};
static const ProtobufCEnumValueIndex status__enum_values_by_name[8] =
{
  { "CryptoError", 6 },
  { "InternalError", 5 },
  { "InvalidArgument", 4 },
  { "InvalidProto", 2 },
  { "InvalidSecScheme", 1 },
  { "InvalidSession", 7 },
  { "Success", 0 },
  { "TooManySessions", 3 },
};
const ProtobufCEnumDescriptor status__descriptor =
{
  PROTOBUF_C__ENUM_DESCRIPTOR_MAGIC,
  "Status",
  "Status",
  "Status",
  "",
  8,
  status__enum_values_by_number,
  8,
  status__enum_values_by_name,
  1,
  status__value_ranges,
  NULL,NULL,NULL,NULL   /* reserved[1234] */
};
