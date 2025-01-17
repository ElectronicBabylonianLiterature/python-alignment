from enum import IntEnum
import sys

from six import text_type
from six.moves import range

from abc import ABCMeta, ABC
from abc import abstractmethod

from .sequence import GAP_CODE
from .sequence import EncodedSequence


# Scoring ---------------------------------------------------------------------

class Scoring(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __call__(self, firstElement, secondElement):
        return 0


class GapScoring(ABC):
    @abstractmethod
    def gapStart(self, element):
        ...

    @abstractmethod
    def gapExtension(self, element):
        ...
    


class SimpleScoring(GapScoring, Scoring):

    def __init__(self, matchScore, mismatchScore, gapStartScore = 0, gapExtensionScore = 0):
        self.matchScore = matchScore
        self.mismatchScore = mismatchScore
        self.gapStartScore = gapStartScore
        self.gapExtensionScore = gapExtensionScore

    def __call__(self, firstElement, secondElement):
        if firstElement == secondElement:
            return self.matchScore
        else:
            return self.mismatchScore

    def gapStart(self, element):
        return self.gapStartScore

    def gapExtension(self, element):
        return self.gapExtensionScore


# Alignment -------------------------------------------------------------------

class SequenceAlignment(object):

    def __init__(self, first, second, gap=GAP_CODE, other=None):
        self.first = first
        self.second = second
        self.gap = gap
        if other is None:
            self.scores = [0] * len(first)
            self.score = 0
            self.identicalCount = 0
            self.similarCount = 0
            self.gapCount = 0
            self.preservedCount = 0
        else:
            self.scores = list(other.scores)
            self.score = other.score
            self.identicalCount = other.identicalCount
            self.similarCount = other.similarCount
            self.gapCount = other.gapCount
            self.preservedCount = other.preservedCount

    def push(self, firstElement, secondElement, score=0):
        self.first.push(firstElement)
        self.second.push(secondElement)
        self.scores.append(score)
        self.score += score
        if firstElement == secondElement:
            self.identicalCount += 1
        if score > 0:
            self.similarCount += 1
        if firstElement == self.gap or secondElement == self.gap:
            self.gapCount += 1
        else:
            self.preservedCount += 1

    def pop(self):
        firstElement = self.first.pop()
        secondElement = self.second.pop()
        score = self.scores.pop()
        self.score -= score
        if firstElement == secondElement:
            self.identicalCount -= 1
        if score > 0:
            self.similarCount -= 1
        if firstElement == self.gap or secondElement == self.gap:
            self.gapCount -= 1
        else:
            self.preservedCount -= 1
        return firstElement, secondElement

    def key(self):
        return self.first.key(), self.second.key()

    def reversed(self):
        first = self.first.reversed()
        second = self.second.reversed()
        return type(self)(first, second, self.gap, self)

    def percentIdentity(self):
        try:
            return float(self.identicalCount) / len(self) * 100.0
        except ZeroDivisionError:
            return 0.0
    
    def percentPreservedIdentity(self):
        try:
            return float(self.identicalCount) / self.preservedCount * 100.0
        except ZeroDivisionError:
            return 0.0

    def percentSimilarity(self):
        try:
            return float(self.similarCount) / len(self) * 100.0
        except ZeroDivisionError:
            return 0.0
    
    def percentPreservedSimilarity(self):
        try:
            return float(self.similarCount) / self.preservedCount * 100.0
        except ZeroDivisionError:
            return 0.0

    def percentGap(self):
        try:
            return float(self.gapCount) / len(self) * 100.0
        except ZeroDivisionError:
            return 0.0

    def quality(self):
        return self.score, \
            self.percentIdentity(), \
            self.percentSimilarity(), \
            -self.percentGap()

    def __len__(self):
        assert len(self.first) == len(self.second)
        return len(self.first)

    def __getitem__(self, item):
        return self.first[item], self.second[item]

    def __repr__(self):
        return repr((self.first, self.second))

    def __str__(self):
        first = [str(e) for e in self.first.elements]
        second = [str(e) for e in self.second.elements]
        for i in range(len(first)):
            n = max(len(first[i]), len(second[i]))
            format = '%-' + str(n) + 's'
            first[i] = format % first[i]
            second[i] = format % second[i]
        return '%s\n%s' % (' '.join(first), ' '.join(second))

    def __unicode__(self):
        first = [text_type(e) for e in self.first.elements]
        second = [text_type(e) for e in self.second.elements]
        for i in range(len(first)):
            n = max(len(first[i]), len(second[i]))
            format = u'%-' + text_type(n) + u's'
            first[i] = format % first[i]
            second[i] = format % second[i]
        return u'%s\n%s' % (u' '.join(first), u' '.join(second))


# Aligner ---------------------------------------------------------------------
def make_matrix(shape, factory):
    i, j = shape
    result = []
    for col in range(0, i):
        result.append([])
        for row in range(0, j):
            result[col].append(factory())
            
    return result

class MatrixType(IntEnum):
    F = 1
    IX = 2
    IY = 3

class AlignmentMatrix:
    def __init__(self, shape=(0,0)):
        self.shape = shape
        self.matrix = {
            MatrixType.F: make_matrix(shape, int),
            MatrixType.IX: make_matrix(shape, int),
            MatrixType.IY: make_matrix(shape, int)
        }
        self.direction = {
            MatrixType.F: make_matrix(shape, list),
            MatrixType.IX: make_matrix(shape, list),
            MatrixType.IY: make_matrix(shape, list)
        }

    def getScore(self, type, i, j):
        return self.matrix[type][i][j]

    def setScore(self, type, i, j, score):
        self.matrix[type][i][j] = score

    def getDirection(self, type, i, j):
        return self.direction[type][i][j]

    def setDirection(self, type, i, j, direction):
        self.direction[type][i][j] = direction
    
    def max(self):
        return max(
            max(map(max, self.matrix[type])) for type in MatrixType
        )

class SequenceAligner(object):
    __metaclass__ = ABCMeta

    def __init__(self, scoring, gapScore, gapExtensionScore):
        self.scoring = scoring
        self.gapScore = gapScore
        self.gapExtensionScore = gapExtensionScore

    def align(self, first, second, backtrace=False):
        f = self.computeAlignmentMatrix(first, second)
        score = self.bestScore(f)
        if backtrace:
            alignments = self.backtrace(first, second, f)
            return score, alignments
        else:
            return score

    def emptyAlignment(self, first, second):
        # Pre-allocate sequences.
        return SequenceAlignment(
            EncodedSequence(len(first) + len(second), id=first.id),
            EncodedSequence(len(first) + len(second), id=second.id),
        )

    @abstractmethod
    def computeAlignmentMatrix(self, first, second):
        return AlignmentMatrix()

    @abstractmethod
    def bestScore(self, f):
        return 0

    @abstractmethod
    def backtrace(self, first, second, f):
        return list()


class GlobalSequenceAligner(SequenceAligner):

    def __init__(self, scoring, fastBacktrace=False):
        super(GlobalSequenceAligner, self).__init__(scoring, 0, 0)
        self._fastBacktrace = fastBacktrace

    def computeAlignmentMatrix(self, first, second):
        m = len(first) + 1
        n = len(second) + 1
        f = AlignmentMatrix((m,n))
        for i in range(1, m):
            for j in range(1, n):
                # Match elements.
                prevF = f.getScore(MatrixType.F ,i - 1, j - 1)
                prevIx = f.getScore(MatrixType.IX ,i - 1, j - 1)
                prevIy = f.getScore(MatrixType.IY ,i - 1, j - 1)
                maxScore = max(prevF, prevIx, prevIy)
                dirAb = [
                    dir for
                    score, dir in [
                        (prevF, MatrixType.F),
                        (prevIx, MatrixType.IX),
                        (prevIy, MatrixType.IY)
                    ]
                    if score == maxScore
                ]
                f.setScore(MatrixType.F ,i, j, maxScore + self.scoring(first[i - 1], second[j - 1]))
                f.setDirection(MatrixType.F ,i, j, dirAb)

                # Gap on first sequence.
                if i == m - 1:
                    prevF = f.getScore(MatrixType.F ,i, j - 1)
                    prevIx = f.getScore(MatrixType.IX ,i, j - 1)
                    prevIy = f.getScore(MatrixType.IY ,i, j - 1)
                    maxScore = max(prevF, prevIx, prevIy)
                    dirGa = [
                        dir for
                        score, dir in [
                            (prevF, MatrixType.F),
                            (prevIx, MatrixType.IX),
                            (prevIy, MatrixType.IY)
                        ]
                        if score == maxScore
                    ]
                    f.setScore(MatrixType.IX ,i, j, maxScore)
                    f.setDirection(MatrixType.IX ,i, j, dirGa)
                else:
                    prevF = f.getScore(MatrixType.F ,i, j - 1) + self.scoring.gapStart(second[j-1])
                    prevIx = f.getScore(MatrixType.IX ,i, j - 1)
                    prevIy = f.getScore(MatrixType.IY ,i, j - 1) + self.scoring.gapStart(second[j-1])
                    maxScore = max(prevF, prevIx, prevIy)
                    dirGa = [
                        dir for
                        score, dir in [
                            (prevF, MatrixType.F),
                            (prevIx, MatrixType.IX),
                            (prevIy, MatrixType.IY)
                        ]
                        if score == maxScore
                    ]
                    f.setScore(MatrixType.IX ,i, j, maxScore + self.scoring.gapExtension(second[j-1]))
                    f.setDirection(MatrixType.IX ,i, j, dirGa)

                # Gap on second sequence.
                if j == n - 1:
                    prevF = f.getScore(MatrixType.F ,i - 1, j)
                    prevIx = f.getScore(MatrixType.IX ,i - 1, j)
                    prevIy = f.getScore(MatrixType.IY ,i - 1, j)
                    maxScore = max(prevF, prevIx, prevIy)
                    dirGb = [
                        dir for
                        score, dir in [
                            (prevF, MatrixType.F),
                            (prevIx, MatrixType.IX),
                            (prevIy, MatrixType.IY)
                        ]
                        if score == maxScore
                    ]
                    f.setScore(MatrixType.IY ,i,j, maxScore)
                    f.setDirection(MatrixType.IY ,i, j, dirGb)
                else:
                    prevF = f.getScore(MatrixType.F ,i - 1, j) + self.scoring.gapStart(first[i-1])
                    prevIx = f.getScore(MatrixType.IX ,i - 1, j) + self.scoring.gapStart(first[i-1])
                    prevIy = f.getScore(MatrixType.IY ,i - 1, j)
                    maxScore = max(prevF, prevIx, prevIy)
                    dirGb = [
                        dir for
                        score, dir in [
                            (prevF, MatrixType.F),
                            (prevIx, MatrixType.IX),
                            (prevIy, MatrixType.IY)
                        ]
                        if score == maxScore
                    ]
                    f.setScore(MatrixType.IY ,i,j, maxScore + self.scoring.gapExtension(first[i-1]))
                    f.setDirection(MatrixType.IY ,i, j, dirGb)

        return f

    def bestScore(self, f):
        return max(f.getScore(type_, -1, -1) for type_ in MatrixType)

    def backtrace(self, first, second, f):
        m, n = f.shape
        alignments = list()
        alignment = self.emptyAlignment(first, second)

        bestTypes = [
            type_ for type_ in MatrixType
            if (f.getScore(type_, -1, -1) >= self.bestScore(f))
        ]

        for type_ in bestTypes[:1] if self._fastBacktrace else bestTypes:
                self.backtraceFrom(first, second, f, m - 1, n - 1, alignments, alignment, type_)
        
        return alignments

    def backtraceFrom(self, first, second, f, i, j, alignments, alignment, current):
        if i == 0 or j == 0:
            if current == MatrixType.F:
                alignments.append(alignment.reversed())
        else:
            m, n = f.shape
            allDirections = f.getDirection(current, i, j)
            directions = allDirections[:1] if self._fastBacktrace else allDirections
            c = f.getScore(current, i, j)
            a = first[i - 1]
            b = second[j - 1]

            if current == MatrixType.F:
                for dir in directions:
                    p = f.getScore(dir, i - 1, j - 1)
                    alignment.push(a, b, c - p)
                    self.backtraceFrom(first, second, f, i - 1, j - 1,
                                    alignments, alignment, dir)
                    alignment.pop()
            elif current == MatrixType.IX:
                if i == m - 1:
                    for dir in directions:
                        y = f.getScore(dir, i, j - 1)
                        if c == y:
                            self.backtraceFrom(first, second, f, i, j - 1,
                                               alignments, alignment, dir)
                else: 
                    for dir in directions:
                        y = f.getScore(dir, i, j - 1)
                        alignment.push(alignment.gap, b, c - y)
                        self.backtraceFrom(first, second, f, i, j - 1,
                                           alignments, alignment, dir)
                        alignment.pop()
            elif current == MatrixType.IY:
                if j == n - 1:
                     for dir in directions:
                        x = f.getScore(dir, i - 1, j)
                        if c == x:
                            self.backtraceFrom(first, second, f, i - 1, j,
                                            alignments, alignment, dir)
                else:
                    for dir in directions:
                        x = f.getScore(dir, i - 1, j)
                        alignment.push(a, alignment.gap, c - x)
                        self.backtraceFrom(first, second, f, i - 1, j,
                                        alignments, alignment, dir)
                        alignment.pop()


class StrictGlobalSequenceAligner(SequenceAligner):

    def __init__(self, scoring, gapScore, gapExtensionScore):
        super(StrictGlobalSequenceAligner, self).__init__(scoring, gapScore, gapExtensionScore)

    def computeAlignmentMatrix(self, first, second):
        m = len(first) + 1
        n = len(second) + 1
        f = AlignmentMatrix((m,n))
        for i in range(1, m):
            f.setScore(MatrixType.F ,i, 0, f.getScore(MatrixType.F ,i - 1, 0) + self.gapScore)
        for j in range(1, n):
            f.setScore(MatrixType.F ,0, j, f.getScore(MatrixType.F ,0, j - 1) + self.gapScore)
        for i in range(1, m):
            for j in range(1, n):
                # Match elements.
                ab = f.getScore(MatrixType.F ,i - 1, j - 1) \
                    + self.scoring(first[i - 1], second[j - 1])

                # Gap on first sequence.
                ga = f.getScore(MatrixType.F ,i, j - 1) + self.gapScore

                # Gap on second sequence.
                gb = f.getScore(MatrixType.F ,i - 1, j) + self.gapScore

                f.setScore(MatrixType.F ,i, j, max(ab, ga, gb))
        return f

    def bestScore(self, f):
        return f.getScore(MatrixType.F ,-1, -1)

    def backtrace(self, first, second, f):
        m, n = f.shape
        alignments = list()
        alignment = self.emptyAlignment(first, second)
        self.backtraceFrom(first, second, f, m - 1, n - 1,
                           alignments, alignment)
        return alignments

    def backtraceFrom(self, first, second, f, i, j, alignments, alignment):
        if i == 0 and j == 0:
            alignments.append(alignment.reversed())
        else:
            c = f.getScore(MatrixType.F ,i, j)
            if i != 0:
                x = f.getScore(MatrixType.F ,i - 1, j)
                a = first[i - 1]
                if c == x + self.gapScore:
                    alignment.push(a, alignment.gap, c - x)
                    self.backtraceFrom(first, second, f, i - 1, j,
                                       alignments, alignment)
                    alignment.pop()
                    return
            if j != 0:
                y = f.getScore(MatrixType.F ,i, j - 1)
                b = second[j - 1]
                if c == y + self.gapScore:
                    alignment.push(alignment.gap, b, c - y)
                    self.backtraceFrom(first, second, f, i, j - 1,
                                       alignments, alignment)
                    alignment.pop()
            if i != 0 and j != 0:
                p = f.getScore(MatrixType.F ,i - 1, j - 1)
                # Silence the code inspection warning. We know at this point
                # that a and b are assigned to values.
                # noinspection PyUnboundLocalVariable
                if c == p + self.scoring(a, b):
                    alignment.push(a, b, c - p)
                    self.backtraceFrom(first, second, f, i - 1, j - 1,
                                       alignments, alignment)
                    alignment.pop()


class LocalSequenceAligner(SequenceAligner):

    def __init__(self, scoring, minScore=None):
        super(LocalSequenceAligner, self).__init__(scoring, 0, 0)
        self.minScore = minScore

    def computeAlignmentMatrix(self, first, second):
        m = len(first) + 1
        n = len(second) + 1
        f = AlignmentMatrix((m, n))
        min = -sys.maxsize

        for i in range(1, m):
            f.setScore(MatrixType.F, i, 0, min)
            f.setScore(MatrixType.IX, i, 0, min)
            f.setScore(MatrixType.IY, i, 0, max(0, self.gapScore + i * self.gapExtensionScore))
            f.setDirection(MatrixType.IY, i, 0, [MatrixType.IY])

        for i in range(1, n):
            f.setScore(MatrixType.F, 0, i, min)
            f.setScore(MatrixType.IX, 0, i, max(0, self.gapScore + i * self.gapExtensionScore))
            f.setScore(MatrixType.IY, 0, i, min)
            f.setDirection(MatrixType.IX, 0, i, [MatrixType.IX])

        f.setScore(MatrixType.IX, 0, 0, min)
        f.setScore(MatrixType.IY, 0, 0, min)

        for i in range(1, m):
            for j in range(1, n):
                # Match elements.
                prevF = f.getScore(MatrixType.F ,i - 1, j - 1)
                prevIx = f.getScore(MatrixType.IX ,i - 1, j - 1)
                prevIy = f.getScore(MatrixType.IY ,i - 1, j - 1)
                maxScore = max(prevF, prevIx, prevIy)
                dirAb = [
                    dir for
                    score, dir in [
                        (prevF, MatrixType.F),
                        (prevIx, MatrixType.IX),
                        (prevIy, MatrixType.IY)
                    ]
                    if score == maxScore
                ]
                f.setScore(MatrixType.F ,i, j, max(0, maxScore + self.scoring(first[i - 1], second[j - 1])))
                f.setDirection(MatrixType.F ,i, j, dirAb if maxScore > 0 else dirAb[:1])

                # Gap on sequenceA.
                prevF = f.getScore(MatrixType.F ,i, j - 1) + self.scoring.gapStart(second[j-1])
                prevIx = f.getScore(MatrixType.IX ,i, j - 1)
                prevIy = f.getScore(MatrixType.IY ,i, j - 1) + self.scoring.gapStart(second[j-1])
                maxScore = max(prevF, prevIx, prevIy)
                dirGa = [
                    dir for
                    score, dir in [
                        (prevF, MatrixType.F),
                        (prevIx, MatrixType.IX),
                        (prevIy, MatrixType.IY)
                    ]
                    if score == maxScore
                ]
                f.setScore(MatrixType.IX ,i, j, max(0, maxScore + self.scoring.gapExtension(second[j-1])))
                f.setDirection(MatrixType.IX ,i, j, dirGa)

                # Gap on sequenceB.
                prevF = f.getScore(MatrixType.F ,i - 1, j) + self.scoring.gapStart(first[i-1])
                prevIx = f.getScore(MatrixType.IX ,i - 1, j) + self.scoring.gapStart(first[i-1])
                prevIy = f.getScore(MatrixType.IY ,i - 1, j)
                maxScore = max(prevF, prevIx, prevIy)
                dirGb = [
                    dir for
                    score, dir in [
                        (prevF, MatrixType.F),
                        (prevIx, MatrixType.IX),
                        (prevIy, MatrixType.IY)
                    ]
                    if score == maxScore
                ]
                f.setScore(MatrixType.IY ,i,j, max(0, maxScore + self.scoring.gapExtension(first[i-1])))
                f.setDirection(MatrixType.IY ,i, j, dirGb)

        return f

    def bestScore(self, f):
        return f.max()

    def backtrace(self, first, second, f):
        m, n = f.shape
        alignments = list()
        alignment = self.emptyAlignment(first, second)
        minScore = self.bestScore(f) if self.minScore is None else self.minScore 

        for i in range(m):
            for j in range(n):
                if f.getScore(MatrixType.F ,i, j) >= minScore:
                    self.backtraceFrom(first, second, f, i, j, alignments, alignment, MatrixType.F)

        return alignments

    def backtraceFrom(self, first, second, f, i, j, alignments, alignment, current):
        if f.getScore(current, i, j) == 0:
            alignments.append(alignment.reversed())
        else:
            directions = f.getDirection(current, i, j)
            c = f.getScore(current, i, j)
            a = first[i - 1]
            b = second[j - 1]

            if current == MatrixType.F:
                for dir in directions:
                    p = f.getScore(dir, i - 1, j - 1)
                    alignment.push(a, b, c - p)
                    self.backtraceFrom(first, second, f, i - 1, j - 1,
                                    alignments, alignment, dir)
                    alignment.pop()
            elif current == MatrixType.IX:
                for dir in directions:
                    y = f.getScore(dir, i, j - 1)
                    alignment.push(alignment.gap, b, c - y)
                    self.backtraceFrom(first, second, f, i, j - 1,
                                        alignments, alignment, dir)
                    alignment.pop()
            elif current == MatrixType.IY:
                for dir in directions:
                    x = f.getScore(dir, i - 1, j)
                    alignment.push(a, alignment.gap, c - x)
                    self.backtraceFrom(first, second, f, i - 1, j,
                                        alignments, alignment, dir)
                    alignment.pop()
