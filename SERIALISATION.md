# Serialisation

These notes are a discussion of the serialisation libraries available to
MicroPython plus a tutorial on the use of a library supporting Google Protocol
Buffers (here abbreviated to `protobuf`). The aim is not to replace official
documentation but to illustrate the relative merits and drawbacks of the
various approaches.

##### [Main readme](./README.md)

# 1. The problem

The need for serialisation arises whenever data must be stored on disk or
communicated over an interface such as a socket, a UART or such interfaces as
I2C or SPI. All these require the data to be presented as linear sequences of
bytes. The problem is how to convert an arbitrary Python object to such a
sequence, and how subsequently to restore the object.

There are numerous standards for achieving this, five of which are readily
available to MicroPython. Each has its own advantages and drawbacks. In two
cases the encoded strings aim to be human readable and comprise ASCII
characters. In the others they comprise binary `bytes` objects where bytes can
take all possible values. The following are the formats with MicroPython
support:

 1. ujson (ASCII, official)
 2. pickle (ASCII, official)
 3. ustruct (binary, official)
 4. MessagePack [binary, unofficial](https://github.com/peterhinch/micropython-msgpack)
 5. protobuf [binary, unofficial](https://github.com/dogtopus/minipb)

The `ujson` and `pickle` formats produce human-readable byte sequences. These
aid debugging. The use of ASCII data means that a delimiter can be used to
identify the end of a message. This is because it is possible to guarantee that
the delimiter will never occur within a message. A delimiter cannot be used
with binary formats because a message byte can take all possible values
including that of the delimiter. The drawback of ASCII formats is inefficiency:
the byte sequences are relatively long.

Numbers 1, 2 and 4 are self-describing: the format includes a definition of its
structure. This means that the decoding process can re-create the object in the
absence of information on its structure, which may therefore change at runtime.
Self describing formats inevitably are variable length. This is no problem
where data is being saved to file, but if it is being communicated across a
link the receiving process needs a means to determine when a complete message
has been received. In the case of ASCII formats a delimiter may be used but in
the case of `MessagePack` this presents something of a challenge.

The `ustruct` format is binary: the byte sequence comprises binary data which
is neither human readable nor self-describing. The problem of message framing
is solved by hard coding a fixed message structure and length which is known to
transmitter and receiver. In simple cases of fixed format data, `ustruct`
provides a simple, efficient solution.

In `protobuf` and `MessagePack` messages are variable length; both can handle
data whose length varies at runtime. `MessagePack` also allows the message
structure to change at runtime. It is also extensible to enable the efficient
coding of additional Python types or instances of user defined classes.

The `protobuf` standard requires transmitter and receiver to share a schema
which defines the message structure. Message length may change at runtime, but
structure may not.

There has been some discussion of supporting [CBOR](https://cbor.io/). There is a
MicroPython library [here](https://github.com/onetonfoot/micropython-cbor). This
is a binary format with a focus on minimising message length. I have not yet had
time to study this.

## 1.1 Transmission over unreliable links

Consider a system where a transmitter periodically sends messages to a receiver
over a communication link. An aspect of the message framing problem arises if
that link is unreliable, meaning that bytes may be lost or corrupted in
transit. In the case of ASCII formats with a delimiter the receiver, once it
has detected the problem, can discard characters until the delimiter is
received and then wait for a complete message.

In the case of binary formats it is generally impossible to re-synchronise to a
continuous stream of data. In the case of regular bursts of data a timeout can
be used. Otherwise "out of band" signalling is required where the receiver
signals the transmitter to request retransmission.

## 1.2 Concurrency

In `asyncio` systems the transmitter presents no problem. A message is created
using synchronous code, then transmitted using asynchronous code typically with
a `StreamWriter`. In the case of ASCII protocols a delimiter - usually `b"\n"`
is appended.

In the case of ASCII protocols the receiver can use `StreamReader.readline()`
to await a complete message.

`ustruct` also presents a simple case in that the number of expected bytes is
known to the receiver which simply awaits that number.

The variable length binary protocols present a difficulty in that the message
length is unknown in advance. A solution is available for `MessagePack`.

# 2. ujson and pickle

These are very similar. `ujson` is documented
[here](http://docs.micropython.org/en/latest/library/ujson.html). `pickle` has
identical methods so this doc may be used for both.

The advantage of `ujson` is that JSON strings can be accepted by CPython and by
other languages. The drawback is that only a subset of Python object types can
be converted to legal JSON strings; this is a limitation of the
[JSON specification](http://www.ecma-international.org/publications/files/ECMA-ST/ECMA-404.pdf).

The advantage of `pickle` is that it will accept any Python object except for
instances of user defined classes. The extremely simple source may be found in
[the official library](https://github.com/micropython/micropython-lib/tree/master/python-stdlib/pickle).
The strings produced are incompatible with CPython's `pickle`, but can be
decoded in CPython by using the MicroPython decoder. There is a
[bug](https://github.com/micropython/micropython/issues/2280) in the
MicroPython implementation when running under MicroPython. A workround consists
of never encoding short strings which change repeatedly.

## 2.1 Usage examples

These may be copy-pasted to the MicroPython REPL.  
Pickle:  
```python
import pickle
data = {1:'test', 2:1.414, 3: [11, 12, 13]}
s = pickle.dumps(data)
print('Human readable data:', s)
v = pickle.loads(s)
print('Decoded data (partial):', v[3])
```
JSON. Note that dictionary keys must be strings:  
```python
import ujson
data = {'1':'test', '2':1.414, '3': [11, 12, 13]}
s = ujson.dumps(data)
print('Human readable data:', s)
v = ujson.loads(s)
print('Decoded data (partial):', v['3'])
```

## 2.2 Strings are variable length

In real applications the data, and hence the string length, vary at runtime.
The receiving process needs to know when a complete string has been received or
read from a file. In practice `ujson` and `pickle` do not include newline
characters in encoded strings. If the data being encoded includes a newline, it
is escaped in the string:
```python
import ujson
data = {'1':b'test\nmore', '2':1.414, '3': [11, 12, 13]}
s = ujson.dumps(data)
print('Human readable data:', s)
v = ujson.loads(s)
print('Decoded data (partial):', v['1'])
```
If this is pasted at the REPL you will observe that the human readable data
does not have a line break (while the decoded data does). Output:
```
Human readable data: {"2": 1.414, "3": [11, 12, 13], "1": "test\nmore"}
Decoded data (partial): test
more
```
Consequently encoded strings may be separated with `'\n'` before saving and
reading may be done using `readline` methods as in this code fragment where
`u` is a UART instance:

```python
s = ujson.dumps(data)
# pickle produces a bytes object whereas ujson produces a string
# In the case of ujson it is probably wise to convert to bytes
u.write(s.encode())
# Pickle:
# u.write(s)
u.write(b'\n')

# receiver
s = u.readline()
v = ujson.loads(s)  # ujson can cope with bytes object
# ujson and pickle can cope with trailing newline.
```

# 3. ustruct

This is documented
[here](http://docs.micropython.org/en/latest/library/ustruct.html). The binary
format is efficient, but the format of a sequence cannot change at runtime and
must be "known" to the decoding process. Records are of fixed length. If data
is to be stored in a binary random access file, the fixed record size means
that the offset of a given record may readily be calculated.

Write a 100 record file. Each record comprises three 32-bit integers:  
```python
import ustruct
fmt = 'iii'  # Record format: 3 signed ints
rlen = ustruct.calcsize(fmt)  # Record length
buf = bytearray(rlen)
with open('myfile', 'wb') as f:
    for x in range(100):
        y = x * x
        z = x * 10
        ustruct.pack_into(fmt, buf, 0, x, y, z)
        f.write(buf)
```
Read record no. 10 from that file:  
```python
import ustruct
fmt = 'iii'
rlen = ustruct.calcsize(fmt)  # Record length
buf = bytearray(rlen)
rnum = 10  # Record no.
with open('myfile', 'rb') as f:
    f.seek(rnum * rlen)
    f.readinto(buf)
    result = ustruct.unpack_from(fmt, buf)
print(result)
```
Owing to the fixed record length, integers must be constrained to fit the
length declared in the format string.

Binary formats cannot use delimiters as any delimiter character may be present
in the data - however the fixed length of `ustruct` records means that this is
not a problem.

For performance oriented applications, `ustruct` is the only serialisation
approach which can be used in a non-allocating fashion, by using pre-allocated
buffers as in the above example.

## 3.1 Strings

In `ustruct` the `s` data type is normally prefixed by a length (defaulting to
1). This ensures that records are of fixed size, but is potentially inefficient
as shorter strings will still occupy the same amount of space. Longer strings
will silently be truncated. Short strings are packed with zeros.

```python
import ustruct
fmt = 'ii30s'
rlen = ustruct.calcsize(fmt)  # Record length
buf = bytearray(rlen)
ustruct.pack_into(fmt, buf, 0, 11, 22, 'the quick brown fox')
ustruct.unpack_from(fmt, buf)
ustruct.pack_into(fmt, buf, 0, 11, 22, 'rats')
ustruct.unpack_from(fmt, buf)  # Packed with zeros
ustruct.pack_into(fmt, buf, 0, 11, 22, 'the quick brown fox jumps over the lazy dog')
ustruct.unpack_from(fmt, buf)  # Truncation
```
Output:
```python
(11, 22, b'the quick brown fox\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
(11, 22, b'rats\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
(11, 22, b'the quick brown fox jumps over')
```

# 4. MessagePack

Of the binary formats this is the easiest to use and can be a "drop in"
replacement for `ujson` as it supports the same four methods `dump`, `dumps`,
`load` and `loads`. An application might initially be developed with `ujson`,
the protocol being changed to `MessagePack` later. Creation of a `MessagePack`
string can be done with:
```python
import umsgpack
obj = [1.23, 2.56, 89000]
msg = umsgpack.dumps(obj)  # msg is a bytes object
```
Retrieval of the object is as follows:
```python
import umsgpack
# Retrieve the message msg
obj = umsgpack.dumps(msg)
```
An ingenious feature of the standard is its extensibility. This can be used to
add support for additional Python types or user defined classes. This example
shows `complex` data being supported as if it were a native type:
```python
import umsgpack
from umsgpack_ext import mpext
with open('data', 'wb') as f:
   umsgpack.dump(mpext(1 + 4j), f)  # mpext() handles extension type
```
Reading back:
```python
import umsgpack
import umsgpack_ext  # Decoder only needs access to this module
with open('data', 'rb') as f:
    z = umsgpack.load(f)
print(z)  # z is complex
```
Please see [this repo](https://github.com/peterhinch/micropython-msgpack). The
docs include references to the standard and to other implementations. The repo
includes an asynchronous receiver which enables incoming messages to be decoded
as they arrive while allowing other tasks to run concurrently.

# 5. Protocol Buffers

This is a [Google standard](https://developers.google.com/protocol-buffers/)
described in [this Wikipedia article](https://en.wikipedia.org/wiki/Protocol_Buffers).
The aim is to provide a language independent, efficient, binary data interface.
Records are variable length, and strings and integers of arbitrary size may be
accommodated. The
[implementation compatible with MicroPython](https://github.com/dogtopus/minipb)
is a "micro" implementation: `.proto` files are not supported. However the data
format aims to be a subset of the Google standard and claims compatibility with
other platforms and languages.

The principal benefit to developers using only CPython/MicroPython is its
efficient support for fields whose length varies at runtime. To my knowledge it
is the sole solution for encoding such data in a compact binary format.

The following notes should be read in conjunction with the official docs. The
notes aim to reduce the learning curve which I found a little challenging.

In normal use the object transmitted by `minipb` will be a `dict` with entries
having various predefined data types. Entries may be objects of variable length
including strings, lists and other `dict` instances. The structure of the
`dict` is defined using a `schema`. Sender and receiver share the `schema` with
each script using it to instantiate the `Wire` class. The `Wire` instance is
then repeatedly invoked to encode or decode the data.

The `schema` is a `tuple` defining the structure of the data `dict`. Each
element declares a key and its data type in an inner `tuple`. Elements of this
inner `tuple` are strings, with element 0 defining the field's key. Subsequent
elements define the field's data type; in most cases the data type is defined
by a single string.

## 5.1 Installation

The library comprises a single file `minipb.py`. It has some dependencies, the
`logging` module `logging.py` and `bisect` module `bisect.py` which may be found in
[micropython-lib](https://github.com/micropython/micropython-lib/tree/master/python-stdlib).
On RAM constrained platforms `minipb.py` may be cross-compiled or frozen as
bytecode for even lower RAM consumption.

## 5.2 Data types

These are listed in
[the docs](https://github.com/dogtopus/minipb/wiki/Schema-Representations).
Many of these are intended to maximise compatibility with the native data types
of other languages. Where data will only be accessed by CPython or MicroPython,
a subset may be used which maps onto Python data types:

 1. 'U' A UTF8 encoded string.
 2. 'a' A `bytes` object.
 3. 'b' A `bool`.
 4. 'f' A `float` A 32-bit float: the usual MicroPython default.
 5. 'z' An `int`: a signed arbitrary length integer. Efficiently encoded with
 an ingenious algorithm.
 6. 'd' A double precision 64-bit float. The default on Pyboard D SF6. Also on
 other platforms with special firmware builds.
 7. 'x' An empty field.

## 5.2.1 Required and Optional fields

If a field is prefixed with `*` it is a `required` field, otherwise it is
optional. The field must still exist in the data: the only difference is that
a `required` field cannot be set to `None`. Optional fields can be useful,
notably for boolean types which can then represent three states.

## 5.3 Application design

The following is a minimal example which can be pasted at the REPL:
```python
import minipb

schema = (('value', 'z'),)  # Dict will hold a single integer
w = minipb.Wire(schema)

data = {'value': 0}
data['value'] = 150
tx = w.encode(data)
rx = w.decode(tx)  # received data
print(rx)
```
This example glosses over the fact that in a real application the data will
change and the length of the transmitted string `tx` will vary. The receiving
process needs to know the length of each string. Note that a consequence of the
binary format is that delimiters cannot be used. The length of each record must
be established and made available to the receiver. In the case where data is
being saved to a binary file, the file will need an index. Where data is to
be transmitted over and interface each string should be prepended with a fixed
length "size" field. The following example illustrates this.

## 5.4 Transmitter/Receiver example

These examples can't be cut and pasted at the REPL as they assume `send(n)` and
`receive(n)` functions which access the interface.

Sender example:
```python
import minipb
schema = (('value', 'z'),
          ('float', 'f'),
          ('signed', 'z'),)
w = minipb.Wire(schema)
# Create a dict to hold the data
data = {'value': 0,
        'float': 0.0,
        'signed' : 0,}
while True:
    # Update values then encode and transmit them, e.g.
    # data['signed'] = get_signed_value()
    tx = w.encode(data)
    # Data lengths may change on each iteration
    # here we encode the length in a single byte
    dlen = len(tx).to_bytes(1, 'little')
    send(dlen)
    send(tx)
```
Receiver example:
```python
import minipb
# schema must match transmitter. Typically both would import this.
schema = (('value', 'z'),
          ('float', 'f'),
          ('signed', 'z'),)

w = minipb.Wire(schema)
while True:
    dlen = receive(1)  # Data length stored in 1 byte
    data = receive(dlen)  # Retrieve actual data
    rx = w.decode(data)
    # Do something with the received dict
```

## 5.5 Repeating fields

This feature enables variable length lists to be encoded. List elements must
all be of the same (declared) data type. In this example the `value` and `txt`
fields are variable length lists denoted by the `'+'` prefix. The `value` field
holds a list of `int` values and `txt` holds strings:  
```python
import minipb
schema = (('value', '+z'),
          ('float', 'f'),
          ('txt', '+U'),
          )
w = minipb.Wire(schema)

data = {'value': [150, 123, 456],
        'float': 1.23,
        'txt' : ['abc', 'def', 'ghi'],
        }
tx = w.encode(data)
rx = w.decode(tx)
print(rx)
data['txt'][1] = 'the quick brown fox'  # Strings have variable length
data['txt'].append('the end')  # List has variable length
data['value'].append(999)  # Variable length
tx = w.encode(data)
rx = w.decode(tx)
print(rx)
```
### 5.5.1 Packed repeating fields

This feature reduces some space overhead of encoded message caused by repeatedly
emitting field headers as seen in regular repeated fields.

```python
>>> import minipb
>>> normal=minipb.Wire('+z')
>>> len(normal.encode(range(10000)))
31744
>>> packed=minipb.Wire('#z')
>>> len(packed.encode(range(10000)))
21748
>>>
```

The author of `minipb` [does not recommend](https://github.com/dogtopus/minipb/issues/6)
their use for strings, bytes and nested messages due to compatibility concerns with the
official Google Protobuf standards, which disallows such use.

## 5.6 Message fields (nested dicts)

The concept of message fields is a Protocol Buffer notion. In MicroPython
terminology a message field contains a `dict` whose contents are defined by
another schema. This enables nested dictionaries whose entries may be any valid
`protobuf` data type.

This is illustrated below. The example extends this by making the field a
variable length list of `dict` objects (with the `'+['` specifier):
```python
import minipb
# Schema for the nested dictionary instances
nested_schema = (('str2', 'U'),
                 ('num2', 'z'),)
# Outer schema
schema = (('number', 'z'),
          ('string', 'U'),
          ('nested', '+[', nested_schema),
          ('num', 'z'),)
w = minipb.Wire(schema)

data = {
    'number': 123,
    'string': 'test',
    'nested': [{'str2': 'string','num2': 888,},
               {'str2': 'another_string', 'num2': 12345,}, ],
    'num' : 42
}
tx = w.encode(data)
rx = w.decode(tx)
print(rx)
print(rx['nested'][0]['str2'])  # Access inner dict instances
print(rx['nested'][1]['str2'])
# Appending to the nested list of dicts
data['nested'].append({'str2': 'rats', 'num2':999})
tx = w.encode(data)
rx = w.decode(tx)
print(rx)
print(rx['nested'][2]['str2'])  # Access inner dict instances
```

### 5.6.1 Recursion

This is surely overkill in most MicroPython applications, but for the sake of
completeness message fields can be recursive:
```python
import minipb
inner_schema = (('str2', 'U'),
                ('num2', 'z'),)

nested_schema = (('inner', '+[', inner_schema),)

schema = (('number', 'z'),
          ('string', 'U'),
          ('nested', '[', nested_schema),
          ('num', 'z'),)

w = minipb.Wire(schema)

data = {
       'number': 123,
       'string': 'test',
       'nested': {'inner':({'str2': 'string', 'num2': 888,},
                           {'str2': 'another_string','num2': 12345,}, ),},
        'num' : 42
        }
tx = w.encode(data)
rx = w.decode(tx)
print(rx)
print(rx['nested']['inner'][0]['str2'])
```
